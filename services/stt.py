# services/stt.py
from openai import OpenAI
from config import settings


DEEINFRA_API_TOKEN=settings.llm_api_key
BASE_URL = settings.BASE_URL

# Make sure to set your DEEPINFRA_API_TOKEN environment variable

def transcribe_audio(file_path: str) -> str:
    """Transcribe audio file to text using DeepInfra's API."""
    client = OpenAI(
        api_key=DEEINFRA_API_TOKEN,
        base_url=BASE_URL,
    )

    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="mistralai/Voxtral-Small-24B-2507",
            file=audio_file
        )

    print(transcript.text)
    #Output:
    #Hello, hi there, how are you? What is the capital of France?
    return transcript.text