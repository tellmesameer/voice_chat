# routes/voice.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models.schemas import ChatRequest, ChatResponse
from db.database import get_db, User, Chat
from services.stt import transcribe_audio
from services.llm import generate_response
from services.pinecone_service import retrieve_context
from services.tts import generate_speech
from datetime import datetime
from config import settings
import os
import uuid
from logger_config import logger  # Import the logger

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
    
    # Check if file is None
    if file.filename is None:
        logger.warning("No file provided in voice upload")
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file type
    if not file.filename.endswith(('.wav', '.mp3', '.m4a')):
        logger.warning(f"Invalid audio file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only audio files (wav, mp3, m4a) are supported")
    
    # Create audio directory if it doesn't exist
    audio_dir = os.path.join(settings.assets_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(audio_dir, unique_filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    logger.info(f"Saved audio file to {file_path}")
    
    # Transcribe audio
    try:
        logger.info("Starting audio transcription")
        transcription = transcribe_audio(file_path)
        logger.info(f"Transcription completed: {transcription}")
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        # Return a more specific error message
        if "401" in str(e):
            raise HTTPException(status_code=500, detail="Authentication error with speech-to-text service")
        raise HTTPException(status_code=500, detail="Error transcribing audio")
    
    # Get or create user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.info(f"Creating new user with ID: {user_id}")
        user = User(user_id=user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Retrieve context from Pinecone for this user
    logger.info(f"Retrieving context for user {user.id}")
    context = retrieve_context(transcription, user.id)  # Pass user.id
    
    # Generate LLM response
    logger.info("Generating LLM response")
    response_text = generate_response(transcription, context)
    
    # Store chat in database
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
    audio_response_path = None
    if generate_audio:
        try:
            # Generate unique filename for audio response
            response_filename = f"{uuid.uuid4()}.mp3"
            audio_response_path = os.path.join(audio_dir, response_filename)
            logger.info(f"Generating audio response to {audio_response_path}")
            generate_speech(response_text, audio_response_path)
            logger.info("Audio response generated successfully")
        except Exception as e:
            logger.error(f"Error generating audio response: {e}")
    
    return ChatResponse(
        response=response_text,
        timestamp=chat_entry.timestamp
    )