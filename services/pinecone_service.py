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
# Initialize Pinecone
pc = Pinecone(api_key=settings.pinecone_api_key)
index = pc.Index(settings.pinecone_index_name)
BASE_URL = settings.BASE_URL

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
        embeddings = openai.embeddings.create(
            model="Qwen/Qwen3-Embedding-8B",
            input=text,
            encoding_format="float"
        )
        # Return the actual embedding vector, not the token count
        return embeddings.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        # Return a zero vector as fallback
        return [0.0] * 1024
def retrieve_context(query: str, top_k: int = 3) -> str:
    """
    Retrieve relevant context from Pinecone based on the query.
    """
    # Generate embedding for the query
    query_embedding = get_embedding(query)
    
    # Query Pinecone
    try:
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        # Extract the text from the metadata
        context_parts = []
        for match in getattr(results, 'matches', []):
            if 'metadata' in match and 'text' in match['metadata']:
                context_parts.append(match['metadata']['text'])
        
        return "\n".join(context_parts) if context_parts else "No relevant context found."
    except Exception as e:
        print(f"Error retrieving context from Pinecone: {e}")
        return "Error retrieving context."
def index_document(file_path: str, document_id: int, db: Session) -> None:
    """
    Parse a PDF document, generate embeddings for each page, and store in Pinecone.
    """
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
        
        # Generate embeddings for each chunk and upsert to Pinecone
        vectors = []
        for i, chunk in enumerate(text_chunks):
            embedding = get_embedding(chunk)
            vectors.append({
                'id': f"doc_{document_id}_chunk_{i}",
                'values': embedding,
                'metadata': {
                    'document_id': document_id,
                    'chunk_index': i,
                    'text': chunk
                }
            })
        
        # Upsert to Pinecone
        if vectors:
            index.upsert(vectors)
        
        # Update the document record in the database to mark as indexed
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.indexed = True
            document.indexed_at = datetime.utcnow()
            db.commit()
            
    except Exception as e:
        print(f"Error indexing document {file_path}: {e}")