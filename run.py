# run.py
import uvicorn
from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )