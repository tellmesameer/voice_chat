# services/tts.py
from pathlib import Path
from openai import OpenAI
from config import settings
from logger_config import logger  # Import the logger

# Create a separate client for TTS
tts_client = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.BASE_URL,
)

MODEL = "hexgrad/Kokoro-82M"
AI_VOICE = "af_bella"
RESPONSE_FORMAT = "wav"

def generate_speech(user_text: str, output_path: str) -> str:
    """Generate speech from text using DeepInfra's API and save to output_path."""
    logger.info(f"Generating speech for text: {user_text[:50]}...")
    
    try:
        speech_file_path = Path(output_path)
        with tts_client.audio.speech.with_streaming_response.create(
            model=MODEL,
            voice=AI_VOICE,
            input=user_text,
            response_format=RESPONSE_FORMAT,
        ) as response:
            response.stream_to_file(speech_file_path)
        
        logger.info(f"Speech generated and saved to: {speech_file_path}")
        return str(speech_file_path)
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        raise