# services/pinecone_client.py
from pinecone import Pinecone
from config import settings
from logger_config import logger

# Initialize Pinecone
pc = Pinecone(api_key=settings.pinecone_api_key)
index = pc.Index(settings.pinecone_index_name)

def get_index():
    """Get the Pinecone index instance."""
    return index

def describe_index_stats():
    """Get statistics about the Pinecone index."""
    try:
        logger.info("Getting Pinecone index statistics")
        stats = index.describe_index_stats()
        logger.info(f"Pinecone stats: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Error getting Pinecone stats: {e}")
        raise