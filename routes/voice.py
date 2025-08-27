# routes/voice.py

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


DEEINFRA_API_TOKEN = os.getenv("voxtral_api_key")
BASE_URL = "https://api.deepinfra.com/v1/openai"
# Make sure to set your DEEPINFRA_API_TOKEN environment variable


client = OpenAI(
    api_key=DEEINFRA_API_TOKEN,
    base_url=BASE_URL,
)

with open("speech.mp3", "rb") as audio_file:
    transcript = client.audio.transcriptions.create(
        model="mistralai/Voxtral-Small-24B-2507",
        file=audio_file
    )

print(transcript.text)
#Output:
#Hello, hi there, how are you? What is the capital of France?



