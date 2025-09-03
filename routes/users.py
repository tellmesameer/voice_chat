# routes/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.database import get_db, User
from db.database import get_or_create_user_by_external_id

router = APIRouter()


@router.get("/resolve/{external_id}")
async def resolve_user(external_id: str, db: Session = Depends(get_db)):
    """Return the DB primary key for a frontend/external user id (create if missing).

    Useful for debugging and to allow the frontend to obtain the server-side canonical id.
    """
    db_id = get_or_create_user_by_external_id(db, external_id)
    return {"external_id": external_id, "db_id": db_id}

class UserCreate(BaseModel):
    user_id: str

@router.post("/register")
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.user_id == user_data.user_id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create new user
    user = User(user_id=user_data.user_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"message": "User created successfully", "user_id": user.user_id}