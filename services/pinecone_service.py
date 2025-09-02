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
from datetime import datetime
from db.database import SessionLocal, Document
from sqlalchemy.orm import Session
from logger_config import logger
from pinecone import Pinecone
import logging
import os

logger = logging.getLogger(__name__)
BASE_URL = settings.BASE_URL
EMBEDDING_MODEL = "intfloat/e5-large-v2"  # or "intfloat/multilingual-e5-large"

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(settings.pinecone_index_name)

# Connect to existing index (make sure env var is set)
INDEX_NAME = settings.pinecone_index_name

if not INDEX_NAME:
    raise RuntimeError("PINECONE_INDEX_NAME is not set in environment variables")

try:
    index = pc.Index(INDEX_NAME)
    logger.info(f"Connected to Pinecone index: {INDEX_NAME}")
except Exception as e:
    logger.error(f"Failed to connect to Pinecone index: {e}")
    index = None


def describe_index_stats():
    """Return Pinecone index stats in JSON-safe form."""
    if index is None:
        raise RuntimeError("Pinecone index is not initialized")

    try:
        stats = index.describe_index_stats()

        # Convert to JSON-serializable
        def make_serializable(obj):
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(i) for i in obj]
            elif hasattr(obj, "model_dump"):
                return make_serializable(obj.model_dump())
            elif hasattr(obj, "__dict__"):
                return make_serializable(vars(obj))
            elif isinstance(obj, (int, float, str, bool)) or obj is None:
                return obj
            else:
                return str(obj)

        return make_serializable(stats)

    except Exception as e:
        logger.error(f"Error retrieving Pinecone stats: {e}")
        raise


# Create an OpenAI client with your deepinfra token and endpoint
openai = OpenAI(
    api_key=settings.llm_api_key,
    base_url=BASE_URL,
)

def get_embedding(text: str) -> list:
    """
    Generate an embedding for the given text using DeepInfra via OpenAI-compatible client.
    NOTE: Don't pass 'dimensions' — the model determines the vector size.
    """
    try:
        text = text or ""
        logger.info("Generating embedding for text of length %d", len(text))
        embeddings = openai.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL,
            encoding_format="float",
        )
        # robust extraction: some SDKs return dict or object
        try:
            embedding = embeddings.data[0].embedding
        except Exception:
            # try alternative shapes
            if isinstance(embeddings, dict):
                embedding = embeddings.get("data", [])[0].get("embedding")
            else:
                embedding = getattr(embeddings.data[0], "embedding", None)

        if not embedding:
            raise ValueError("Embedding returned empty from the API")

        logger.info("Successfully generated embedding of length %d", len(embedding))
        return list(embedding)
    except Exception as e:
        logger.exception("Error generating embedding: %s", e)
        # Return a zero vector fallback matching your index dimension (1024)
        return [0.0] * 1024


def retrieve_context(query: str, user_id: int, top_k: int = 3) -> str:
    """
    Retrieve relevant context from Pinecone based on the query and user_id.
    Handles multiple Pinecone response shapes safely.
    """
    print("Getting user_id in retrieve function--> ", user_id)
    logger.info("Retrieving context for user_id=%s query_len=%d", user_id, len(query or ""))
    print("query--> ", query)
    query_embedding = get_embedding(query)
    print("query_embedding---> ", query_embedding)
    # user_id = 1212
    print("user_id---> ", user_id)
    try:
        resp = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter={"user_id": {"$eq": user_id}},
        )
        print()
        print("getting resp in retrieve function---> ", resp)
        print()
    except Exception as e:
        logger.exception("Pinecone query failed: %s", e)
        print("resp failed----")
        return "Error retrieving context."

    # Normalize matches
    matches = []
    if isinstance(resp, dict):
        matches = resp.get("matches", []) or resp.get("results", [])
    else:
        # object form: try attributes
        matches = getattr(resp, "matches", None) or getattr(resp, "results", None) or []

    context_parts = []
    for m in matches:
        try:
            # m can be dict or object; unify
            meta = m.get("metadata") if isinstance(m, dict) else getattr(m, "metadata", None)
            if not meta:
                # some SDKs nest metadata differently
                meta = m.get("meta") if isinstance(m, dict) else getattr(m, "meta", None)

            text_chunk = None
            if isinstance(meta, dict):
                text_chunk = meta.get("text") or meta.get("original_text") or meta.get("content")
            else:
                text_chunk = getattr(meta, "text", None) if meta else None

            if text_chunk:
                context_parts.append(text_chunk)
        except Exception:
            logger.debug("Failed to parse a match entry: %s", m)

    if not context_parts:
        return "No relevant context found."

    context = "\n".join(context_parts)
    logger.info("Retrieved context length=%d", len(context))
    return context


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


        