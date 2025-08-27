from pathlib import Path
from stt import client

MODEL="hexgrad/Kokoro-82M"
AI_VOICE="af_bella"
RESPONSE_FORMAT="mp3"

def generate_speech(user_text: str, output_path: str):
    """Generate speech from text using DeepInfra's API and save to output_path."""
    speech_file_path = Path(output_path)
    with client.audio.speech.with_streaming_response.create(
      model=MODEL,
      voice=AI_VOICE,
      input=user_text,
      response_format=RESPONSE_FORMAT,
    ) as response:
      response.stream_to_file(speech_file_path)
    return str(speech_file_path)
