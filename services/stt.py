# services/stt.py
from openai import OpenAI
from config import settings
from logger_config import logger
from pydub import AudioSegment
import tempfile
import os

stt_client = OpenAI(
    api_key=settings.stt_api_key,
    base_url=settings.BASE_URL,
)

def transcribe_audio(file_path: str) -> str:
    """Transcribe audio file to text using DeepInfra's API with format conversion."""
    logger.info(f"Transcribing audio file: {file_path}")

    # Create a safe temp file
    temp_input = None
    try:
        # Load audio with pydub and convert
        logger.info("Loading and converting audio for transcription...")
        audio = AudioSegment.from_file(file_path)

        # Convert to 16kHz, mono, 16-bit PCM
        audio = audio.set_frame_rate(16000)
        audio = audio.set_channels(1)  # Mono
        audio = audio.set_sample_width(2)  # 16-bit

        # Export to temp WAV file
        temp_input = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_input.close()
        audio.export(temp_input.name, format="wav", parameters=["-bitexact"])

        logger.info(f"Converted audio saved to temp file: {temp_input.name}")

        # Transcribe the converted file
        with open(temp_input.name, "rb") as f:
            transcript = stt_client.audio.transcriptions.create(
                model="mistralai/Voxtral-Small-24B-2507",
                file=f
            )

        transcription = transcript.text
        logger.info(f"Transcription result: {transcription}")
        return transcription

    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        raise
    finally:
        # Clean up temp file
        if temp_input and os.path.exists(temp_input.name):
            os.unlink(temp_input.name)