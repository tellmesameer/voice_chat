# main.py

from fastapi import FastAPI
from routes import chat, documents, voice, users
from config import APP_NAME, DEBUG
from db.database import init_db
from routes import health   # <-- new
from logger_config import logger  # Import the logger
from fastapi.staticfiles import StaticFiles
import os
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(title=APP_NAME, debug=DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# After app = FastAPI(...)
app.mount("/static", StaticFiles(directory="assets"), name="static")
# Initialize database on startup
@app.on_event("startup")
def startup_event():
    logger.info("Starting up application")
    init_db()
    logger.info("Database initialized")

# Include routers
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(voice.router, prefix="/voice", tags=["voice"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(health.router, prefix="", tags=["health"])  # mounts /health


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": f"Welcome to {APP_NAME}"}