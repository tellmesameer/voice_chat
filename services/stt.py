# services/stt.py
from openai import OpenAI
from config import settings
from logger_config import logger  # Import the logger

# Create a separate client for STT
stt_client = OpenAI(
    api_key=settings.stt_api_key,  # Use STT API key
    base_url=settings.BASE_URL,
)

def transcribe_audio(file_path: str) -> str:
    """Transcribe audio file to text using DeepInfra's API."""
    logger.info(f"Transcribing audio file: {file_path}")
    
    try:
        with open(file_path, "rb") as audio_file:
            transcript = stt_client.audio.transcriptions.create(
                model="mistralai/Voxtral-Small-24B-2507",
                file=audio_file
            )
        logger.info(f"Transcription result: {transcript.text}")
        return transcript.text
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise