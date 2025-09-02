# routes/voice.py
import os
import urllib.parse
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
import json
from sqlalchemy.orm import Session

from config import settings
from db.database import Chat, User, get_db
from logger_config import logger
from models.schemas import ChatResponse
from services.llm import generate_response
from services.pinecone_service import retrieve_context
from services.stt import transcribe_audio
from services.tts import generate_speech
from services.streaming import websocket_stream


router = APIRouter()



@router.post("/upload", response_model=ChatResponse)
async def upload_voice(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    generate_audio: bool = Form(False),
    db: Session = Depends(get_db)
):
    logger.info(f"Voice upload requested by user {user_id}, generate_audio: {generate_audio}")

    if file.filename is None:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(('.wav', '.mp3', '.m4a')):
        raise HTTPException(status_code=400, detail="Only audio files (wav, mp3, m4a) are supported")

    # Create audio directory
    audio_dir = os.path.join(settings.assets_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    # Save uploaded file
    file_extension = file.filename.split('.')[-1].lower()
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(audio_dir, unique_filename)

    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
            f.flush()
            os.fsync(f.fileno())
        logger.info(f"Saved audio file to {file_path}")

        if os.path.getsize(file_path) == 0:
            raise ValueError("Saved file is empty")
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
        raise HTTPException(status_code=500, detail="Transcription failed")

    # Get or create user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.info(f"Creating new user with ID: {user_id}")
        user = User(user_id=user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Retrieve context using numeric user.id
    logger.info(f"Retrieving context for user in voice.py--> {user.user_id} (db id={user.id})")
    # Safely get numeric DB id (avoid passing SQLAlchemy Column objects)
    # uid = getattr(user, 'id', 0) or 0
    uid = user.user_id
    try:
        uid = int(uid)
    except Exception:
        uid = 0
    context = retrieve_context(transcription, uid)
    print("Final output context in voice.py --------> ", context)

    # Generate LLM response
    logger.info("Generating LLM response  - before function execution in - voice.py")
    response_text = generate_response(transcription, context)

    # Store chat in DB
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
            response_filename = f"{uuid.uuid4()}.wav"
            audio_response_path = os.path.join(audio_dir, response_filename)
            logger.info(f"Generating audio response to {audio_response_path}")

            generate_speech(response_text, audio_response_path)

            if os.path.exists(audio_response_path):
                rel_path = os.path.relpath(audio_response_path, settings.assets_dir).replace("\\", "/")
                # rel_path already contains the 'audio/...' prefix under assets
                audio_url = f"/static/{urllib.parse.quote(rel_path)}"
                logger.info(f"Audio response generated: {audio_url}")
            else:
                logger.warning("Audio file was expected but not found")
        except Exception as e:
            logger.error(f"Error generating audio response: {e}")

    # ✅ Return response with audio_url
    return {
        "response": response_text,
        "timestamp": chat_entry.timestamp.isoformat(),
        "audio_url": audio_url
    }


@router.websocket("/ws")
async def websocket_stream_route(websocket: WebSocket):
    # Delegate to service module for clarity
    await websocket_stream(websocket)


