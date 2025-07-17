# db.py
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, func
from enum import Enum

def utc_now() -> datetime:
    """Helper function to get current UTC time."""
    return datetime.now(timezone.utc)

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class IngestionStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
    last_login: Optional[datetime] = None
    
    # Profile information
    full_name: Optional[str] = Field(default=None, max_length=200)
    avatar_url: Optional[str] = None
    
    # Relationships
    queries: List["UserQuery"] = Relationship(back_populates="user")
    documents: List["UserDocument"] = Relationship(back_populates="user")
    sessions: List["UserSession"] = Relationship(back_populates="user")

class UserQuery(SQLModel, table=True):
    __tablename__ = "user_queries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    session_id: Optional[str] = Field(default=None, index=True)
    
    # Query details
    question: str
    answer: str
    context_used: Optional[str] = None  # JSON string of context chunks
    
    # Performance metrics
    response_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="queries")

class UserDocument(SQLModel, table=True):
    __tablename__ = "user_documents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    # Document identification
    document_id: str = Field(unique=True, index=True)  # UUID for external reference
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    content_type: str
    
    # Processing status
    status: IngestionStatus = Field(default=IngestionStatus.QUEUED)
    error_message: Optional[str] = None
    
    # Metrics
    chunk_count: int = Field(default=0)
    total_characters: int = Field(default=0)
    processing_time_ms: Optional[int] = None
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    completed_at: Optional[datetime] = None
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="documents")

class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    session_id: str = Field(unique=True, index=True)
    
    # Session metadata
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    last_activity: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    expires_at: Optional[datetime] = None
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="sessions")
