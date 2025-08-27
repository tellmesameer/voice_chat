# models/schemas.py


from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ChatMessage(BaseModel):
    id: Optional[int] = None
    user_id: str
    message: str
    response: Optional[str] = None
    timestamp: datetime = datetime.now()

class DocumentUpload(BaseModel):
    filename: str
    status: str

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    timestamp: datetime