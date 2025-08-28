# routes/voice.py
import os
import urllib.parse
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from config import settings
from db.database import Chat, User, get_db
from logger_config import logger
from models.schemas import ChatResponse
from services.llm import generate_response
from services.pinecone_service import retrieve_context
from services.stt import transcribe_audio
from services.tts import generate_speech

router = APIRouter()


@router.post("/upload", response_model=ChatResponse)
async def upload_voice(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    generate_audio: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Upload audio file, transcribe it, and get an LLM response.
    Optionally generate audio response.
    """
    logger.info(f"Voice upload requested by user {user_id}, generate_audio: {generate_audio}")

    # Validate file
    if file.filename is None:
        logger.warning("No file provided in voice upload")
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(('.wav', '.mp3', '.m4a')):
        logger.warning(f"Invalid audio file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only audio files (wav, mp3, m4a) are supported")

    # Create audio directory
    audio_dir = os.path.join(settings.assets_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    # Save uploaded file
    file_extension = file.filename.split('.')[-1].lower()
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(audio_dir, unique_filename)

    # Save uploaded file
    try:
        contents = await file.read()
        if len(contents) == 0:
            raise ValueError("Empty file uploaded")

        with open(file_path, "wb") as f:
            f.write(contents)
            f.flush()
            os.fsync(f.fileno())  # Critical on Windows
        logger.info(f"Saved audio file to {file_path}")

        # Confirm file is readable
        if os.path.getsize(file_path) == 0:
            raise RuntimeError("Saved file is empty")
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save audio file")

    # Transcribe audio
    try:
        logger.info("Starting audio transcription")
        transcription = transcribe_audio(file_path)
        logger.info(f"Transcription completed: {transcription}")
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        if "401" in str(e):
            raise HTTPException(status_code=500, detail="Authentication error with STT service")
        raise HTTPException(status_code=500, detail="Transcription failed")

    # Get or create user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.info(f"Creating new user with ID: {user_id}")
        user = User(user_id=user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Retrieve context using user.user_id (string) for Pinecone filtering
    logger.info(f"Retrieving context for user {user.user_id}")
    context = retrieve_context(transcription, user.user_id)

    # Generate LLM response
    logger.info("Generating LLM response")
    response_text = generate_response(transcription, context)

    # Save chat to database
    chat_entry = Chat(
        user_id=user.id,
        message=transcription,
        response=response_text,
        timestamp=datetime.utcnow()
    )
    db.add(chat_entry)
    db.commit()
    db.refresh(chat_entry)
    logger.info(f"Chat entry saved with ID: {chat_entry.id}")

    # Generate audio response if requested
    audio_url = None
    if generate_audio:
        try:
            response_filename = f"{uuid.uuid4()}.mp3"
            audio_response_path = os.path.join(audio_dir, response_filename)
            logger.info(f"Generating audio response to {audio_response_path}")

            generate_speech(response_text, audio_response_path)

            if os.path.exists(audio_response_path):
                # ✅ Fix: Convert backslashes to forward slashes for URLs
                rel_path = os.path.relpath(audio_response_path, settings.assets_dir).replace("\\", "/")
                audio_url = f"/static/audio/{urllib.parse.quote(rel_path)}"
                logger.info(f"Audio response generated: {audio_url}")
            else:
                logger.warning("Audio file was expected but not found")
        except Exception as e:
            logger.error(f"Error generating audio response: {e}")

    # Return response
    return {
        "response": response_text,
        "timestamp": chat_entry.timestamp.isoformat(),
        "audio_url": audio_url
    }