# config.py
import os
from dotenv import load_dotenv
load_dotenv()
# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/smartflow")
BASE_URL = "https://api.deepinfra.com/v1/openai"
# Pinecone settings
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "your-pinecone-api-key")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "voice-chat-index")
# LLM settings
LLM_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
# Application settings
APP_NAME = "SmartFlow Voice Chat"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


class Settings:
    pinecone_api_key: str = PINECONE_API_KEY
    pinecone_environment: str = PINECONE_ENVIRONMENT
    pinecone_index_name: str = PINECONE_INDEX_NAME
    DATABASE_URL: str = DATABASE_URL
    BASE_URL: str = BASE_URL
    llm_api_key: str = LLM_API_KEY
    llm_model: str = LLM_MODEL
    app_name: str = APP_NAME
    debug: bool = DEBUG 
    assets_dir: str = ASSETS_DIR
settings = Settings()