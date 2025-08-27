# main.py
"""
curl "https://api.deepinfra.com/v1/openai/audio/transcriptions" `
  -H "Content-Type: multipart/form-data" `
  -H "Authorization: Bearer 2QZ3o7qfawRr8ByDM5dkobGKtpbn8zSA" `
  -F "file=@D:/AI_Project/voice_chat/speech.mp3" `
  -F "model=mistralai/Voxtral-Small-24B-2507"
"""
from fastapi import FastAPI
from routes import chat, documents, voice
from config import APP_NAME, DEBUG
from db.database import init_db

app = FastAPI(title=APP_NAME, debug=DEBUG)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Include routers
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(voice.router, prefix="/voice", tags=["voice"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {APP_NAME}"}