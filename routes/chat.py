# routes/chat.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.schemas import ChatRequest, ChatResponse, ChatHistoryResponse
from db.database import get_db, User, Chat
from services.llm import generate_response
from services.pinecone_service import retrieve_context
from datetime import datetime

router = APIRouter()

@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest, db: Session = Depends(get_db)):
    # Get or create user
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        user = User(user_id=request.user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Retrieve context from Pinecone
    context = retrieve_context(request.message)
    
    # Generate LLM response
    response_text = generate_response(request.message, context)
    
    # Store chat in database
    chat_entry = Chat(
        user_id=user.id,
        message=request.message,
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

@router.get("/history/{user_id}", response_model=ChatHistoryResponse)
async def get_history(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    chats = db.query(Chat).filter(Chat.user_id == user.id).order_by(Chat.timestamp.desc()).all()
    
    return ChatHistoryResponse(
        user_id=user_id,
        messages=[
            {
                "id": chat.id,
                "message": chat.message,
                "response": chat.response,
                "timestamp": chat.timestamp
            }
            for chat in chats
        ]
    )


@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest, db: Session = Depends(get_db)):
    # Get or create user
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        user = User(user_id=request.user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Retrieve context from Pinecone for this user
    context = retrieve_context(request.message, user.id)  # Pass user.id
    
    # Generate LLM response
    response_text = generate_response(request.message, context)
    
    # Store chat in database
    chat_entry = Chat(
        user_id=user.id,
        message=request.message,
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