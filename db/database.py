# db\database.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.sql import func
from sqlalchemy import create_engine

from config import settings
# Use the keys from the settings object
DATABASE_URL=settings.DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chats = relationship("Chat", back_populates="user")

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chats")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    content_hash = Column(String, unique=True)  # To prevent duplicate uploads
    indexed = Column(Boolean, default=False)
    indexed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Add user_id foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationship with User
    user = relationship("User", backref="documents")

def init_db():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_user_by_external_id(db: Session, external_user_id: str) -> int:
    """Return the DB primary key for a given external/frontend user identifier.

    If the user does not exist, create it. This centralizes the mapping so
    all services use the DB PK (int) as the canonical user id for Pinecone metadata.
    """
    user = db.query(User).filter(User.user_id == external_user_id).first()
    if not user:
        user = User(user_id=external_user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user.id
