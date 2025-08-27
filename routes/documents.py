# routes/documents.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Form
from models.schemas import DocumentUpload
from db.database import get_db, Document, SessionLocal, User
from services.pinecone_service import index_document
import os
import hashlib
from sqlalchemy.orm import Session
from config import settings
from logger_config import logger  # Import the logger

router = APIRouter()

@router.post("/upload", response_model=DocumentUpload)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), # Dont chagne the order of parameters
    user_id: str = Form(...),  # Add user_id parameter
    db: Session = Depends(get_db)
):
    logger.info(f"Document upload requested by user {user_id}")
    
    # Check if file is None
    if file.filename is None:
        logger.warning("No file provided in document upload")
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename.endswith('.pdf'):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Get user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate file hash to prevent duplicates
    file_content = await file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # Check if document already exists for this user
    existing_doc = db.query(Document).filter(
        Document.content_hash == file_hash,
        Document.user_id == user.id
    ).first()
    if existing_doc:
        logger.info(f"Document already exists for user {user_id}: {existing_doc.filename}")
        return DocumentUpload(
            filename=existing_doc.filename,
            status="already_exists"
        )
    
    # Save file
    os.makedirs(settings.assets_dir, exist_ok=True)
    file_path = os.path.join(settings.assets_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    
    logger.info(f"Saved file to {file_path}")
    
    # Create document record with user_id
    document = Document(
        filename=file.filename,
        file_path=file_path,
        content_hash=file_hash,
        user_id=user.id
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    logger.info(f"Created document record with ID: {document.id}")
    
    # Create a new session for the background task
    new_db = SessionLocal()
    
    # Index document in background
    background_tasks.add_task(index_document, file_path, document.id, user.id, new_db)
    
    logger.info(f"Started background indexing task for document {document.id}")
    
    return DocumentUpload(
        filename=file.filename,
        status="indexing"
    )