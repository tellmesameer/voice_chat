# routes/voice.py
import os
import urllib.parse
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, BackgroundTasks
import json
from sqlalchemy.orm import Session

from config import settings
from db.database import Chat, User, get_db, get_or_create_user_by_external_id
from logger_config import logger
from models.schemas import ChatResponse
from services.llm import generate_response
from services.pinecone_service import retrieve_context, index_transcript
from services.stt import transcribe_audio
from services.tts import generate_speech
from services.streaming import websocket_stream


router = APIRouter()



@router.post("/upload", response_model=ChatResponse)
async def upload_voice(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    generate_audio: bool = Form(False),
    background_tasks: BackgroundTasks = None,
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
    db_user_id = get_or_create_user_by_external_id(db, user_id)
    logger.info(f"Resolved external user_id={user_id} to db_id={db_user_id}")

    # Store transcript immediately in DB as a Chat entry (response will be filled later)
    chat_entry = Chat(
        user_id=db_user_id,
        message=transcription,
        response=None,
        timestamp=datetime.utcnow()
    )
    db.add(chat_entry)
    db.commit()
    db.refresh(chat_entry)
    logger.info(f"Stored transcript as chat id={chat_entry.id} for user db_id={db_user_id}")

    # Schedule background indexing of the transcript (so embeddings are created asynchronously)
    try:
        if background_tasks is not None:
            background_tasks.add_task(index_transcript, db_user_id, transcription, chat_entry.id)
            logger.info("Scheduled background indexing task for chat id=%s", chat_entry.id)
        else:
            # if BackgroundTasks wasn't provided, try to index inline (best-effort)
            index_transcript(db_user_id, transcription, chat_entry.id)
            logger.info("Indexed transcript inline for chat id=%s", chat_entry.id)
    except Exception as e:
        logger.error(f"Failed to schedule/index transcript: {e}")

    # Retrieve context using canonical DB id
    context = retrieve_context(transcription, db_user_id)
    print("Final output context in voice.py --------> ", context)

    # Generate LLM response
    logger.info("Generating LLM response  - before function execution in - voice.py")
    response_text = generate_response(transcription, context)
    print("response_text---> ", response_text)

    # Update existing chat entry with response
    try:
        chat_entry.response = response_text
        chat_entry.timestamp = datetime.utcnow()
        db.add(chat_entry)
        db.commit()
        db.refresh(chat_entry)
        logger.info(f"Updated chat entry id={chat_entry.id} with response")
    except Exception:
        logger.exception("Failed to update chat_entry with response")

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


