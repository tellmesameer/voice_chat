# services/stt.py
from openai import OpenAI
from config import settings

client = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.BASE_URL,
)

def transcribe_audio(file_path: str) -> str:
    """Transcribe audio file to text using DeepInfra's API."""
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="mistralai/Voxtral-Small-24B-2507",
            file=audio_file
        )
    return transcript.text