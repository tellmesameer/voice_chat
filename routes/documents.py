# routes/documents.py

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from models.schemas import DocumentUpload
from db.database import get_db, Document, SessionLocal
from services.pinecone_service import index_document
import os
import hashlib
from sqlalchemy.orm import Session
from config import settings

router = APIRouter()

@router.post("/upload", response_model=DocumentUpload)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    # Check if file is None
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Calculate file hash to prevent duplicates
    file_content = await file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # Check if document already exists
    existing_doc = db.query(Document).filter(Document.content_hash == file_hash).first()
    if existing_doc:
        return DocumentUpload(
            filename=existing_doc.filename,
            status="already_exists"
        )
    
    # Save file
    os.makedirs(settings.assets_dir, exist_ok=True)
    file_path = os.path.join(settings.assets_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    
    # Create document record
    document = Document(
        filename=file.filename,
        file_path=file_path,
        content_hash=file_hash
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Create a new session for the background task
    new_db = SessionLocal()
    
    # Index document in background
    background_tasks.add_task(index_document, file_path, document.id, new_db)
    
    return DocumentUpload(
        filename=file.filename,
        status="indexing"
    )