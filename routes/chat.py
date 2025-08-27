# routes/chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.schemas import ChatRequest, ChatResponse, ChatHistoryResponse
from db.database import get_db, User, Chat
from services.llm import generate_response
from services.pinecone_service import retrieve_context
from datetime import datetime
from logger_config import logger

router = APIRouter()

@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest, db: Session = Depends(get_db)):
    logger.info(f"Received chat message from user {request.user_id}: {request.message}")
    
    # Get or create user
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        logger.info(f"Creating new user with ID: {request.user_id}")
        user = User(user_id=request.user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Retrieve context from Pinecone for this user
    logger.info(f"Retrieving context for user {user.id}")
    context = retrieve_context(request.message, user.id)  # Pass user.id
    
    # Generate LLM response
    logger.info("Generating LLM response")
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
    
    logger.info(f"Chat entry saved with ID: {chat_entry.id}")
    
    return ChatResponse(
        response=response_text,
        timestamp=chat_entry.timestamp
    )

@router.get("/history/{user_id}", response_model=ChatHistoryResponse)
async def get_history(user_id: str, db: Session = Depends(get_db)):
    logger.info(f"Retrieving chat history for user {user_id}")
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    
    chats = db.query(Chat).filter(Chat.user_id == user.id).order_by(Chat.timestamp.desc()).all()
    logger.info(f"Found {len(chats)} chat entries for user {user_id}")
    
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