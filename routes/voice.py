# routes/voice.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models.schemas import ChatRequest, ChatResponse
from db.database import get_db, User, Chat
from services.stt import transcribe_audio
from services.llm import generate_response
from services.pinecone_service import retrieve_context
from datetime import datetime
from config import settings
import os
import uuid

router = APIRouter()

@router.post("/upload", response_model=ChatResponse)
async def upload_voice(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload audio file, transcribe it, and get an LLM response.
    """
    # Check if file is None
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file type
    if not file.filename.endswith(('.wav', '.mp3', '.m4a')):
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
    
    # Transcribe audio
    try:
        transcription = transcribe_audio(file_path)
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail="Error transcribing audio")
    
    # Get or create user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Retrieve context from Pinecone
    context = retrieve_context(transcription)
    
    # Generate LLM response
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
    
    return ChatResponse(
        response=response_text,
        timestamp=chat_entry.timestamp
    )