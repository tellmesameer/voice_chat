# services/pinecone_service.py

# Index configured for llama-text-embed-v2:
# Modality = Text
# Vector type = Dense
# Max input = 2,048 tokens
# Starter limits = 5M tokens
# Index Name = voice-chat-index
# Dimension = 1024
# Metric = cosine

from pinecone import Pinecone
from config import settings
# Use the keys from the settings object
pc = Pinecone(api_key=settings.pinecone_api_key)
index = pc.Index(settings.pinecone_index_name)