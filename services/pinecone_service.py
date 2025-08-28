# services/pinecone_service.py
# Index configured for llama-text-embed-v2:
# Modality = Text
# Vector type = Dense
# Max input = 2,048 tokens
# Starter limits = 5M tokens
# Index Name = voice-chat-index
# Dimension = 1024
# Metric = cosine
from openai import OpenAI
from config import settings
from pinecone import Pinecone
from datetime import datetime
from db.database import SessionLocal, Document
from sqlalchemy.orm import Session
from logger_config import logger

# Initialize Pinecone
pc = Pinecone(api_key=settings.pinecone_api_key)
index = pc.Index(settings.pinecone_index_name)
BASE_URL = settings.BASE_URL
EMBEDDING_MODEL = "intfloat/e5-large-v2"  # or "intfloat/multilingual-e5-large"

# Create an OpenAI client with your deepinfra token and endpoint
openai = OpenAI(
    api_key=settings.llm_api_key,
    base_url=BASE_URL,
)

def get_embedding(text: str) -> list:
    """
    Generate an embedding for the given text using the llama-text-embed-v2 model.
    """
    try:
        logger.info(f"Generating embedding for text of length {len(text)}")
        embeddings = openai.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL,      # or "intfloat/multilingual-e5-large"
            dimensions=1024,
            encoding_format="float",
        )
        # Return the actual embedding vector, not the token count
        embedding = embeddings.data[0].embedding
        logger.info(f"Successfully generated embedding of length {len(embedding)}")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        # Return a zero vector as fallback
        return [0.0] * 1024

def retrieve_context(query: str, user_id: int, top_k: int = 3) -> str:
    """
    Retrieve relevant context from Pinecone based on the query and user_id.
    """
    logger.info(f"Retrieving context for query: '{query}' for user_id: {user_id}")
    
    # Generate embedding for the query
    query_embedding = get_embedding(query)
    
    # Query Pinecone with metadata filter for user_id
    try:
        logger.info(f"Querying Pinecone with user_id filter: {user_id}")
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter={"user_id": {"$eq": user_id}}  # Filter by user_id
        )
        
        # Extract the text from the metadata
        context_parts = []
        matches = results.get('matches', [])
        logger.info(f"Found {len(matches)} matches in Pinecone")
        
        for match in matches:
            if 'metadata' in match and 'text' in match['metadata']:
                context_parts.append(match['metadata']['text'])
                logger.debug(f"Added context chunk of length {len(match['metadata']['text'])}")
        
        context = "\n".join(context_parts) if context_parts else "No relevant context found."
        logger.info(f"Retrieved context of length {len(context)}")
        return context
    except Exception as e:
        logger.error(f"Error retrieving context from Pinecone: {e}")
        return "Error retrieving context."

def index_document(file_path: str, document_id: int, user_id: int, db: Session) -> None:
    """
    Parse a PDF document, generate embeddings for each page, and store in Pinecone.
    """
    logger.info(f"Indexing document {file_path} for user_id {user_id}")
    
    try:
        # Import here to avoid circular imports
        import pdfplumber
        
        # Extract text from PDF
        text_chunks = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    text_chunks.append(text)
                    logger.debug(f"Extracted {len(text)} characters from page {i+1}")
        
        logger.info(f"Extracted {len(text_chunks)} text chunks from PDF")
        
        if not text_chunks:
            logger.warning(f"No text extracted from document {file_path}")
            return
        
        # Generate embeddings for each chunk and upsert to Pinecone
        vectors = []
        for i, chunk in enumerate(text_chunks):
            logger.debug(f"Processing chunk {i+1}/{len(text_chunks)} of length {len(chunk)}")
            embedding = get_embedding(chunk)
            vectors.append({
                'id': f"doc_{document_id}_chunk_{i}",
                'values': embedding,
                'metadata': {
                    'document_id': document_id,
                    'user_id': user_id,  # Add user_id to metadata
                    'chunk_index': i,
                    'text': chunk
                }
            })
        
        # Upsert to Pinecone
        if vectors:
            logger.info(f"Upserting {len(vectors)} vectors to Pinecone")
            response = index.upsert(vectors)
            logger.info(f"Pinecone upsert response: {response}")
        else:
            logger.warning("No vectors to upsert to Pinecone")
        
        # Update the document record in the database to mark as indexed
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.indexed = True
            document.indexed_at = datetime.utcnow()
            db.commit()
            logger.info(f"Updated document {document_id} as indexed")
            
    except Exception as e:
        logger.error(f"Error indexing document {file_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())


        