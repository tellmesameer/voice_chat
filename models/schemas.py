# models/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


class DocumentUpload(BaseModel):
    filename: str
    status: str

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatMessage(BaseModel):
    id: Optional[int] = None
    user_id: str
    message: str
    response: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))



class ChatResponse(BaseModel):
    response: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatHistoryResponse(BaseModel):
    user_id: str
    messages: List[Dict[str, Any]]