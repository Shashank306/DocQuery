# schemas.py
from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr, validator
from app.models.db import UserRole, IngestionStatus

# Authentication Schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, max_length=200)

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    avatar_url: Optional[str]

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None

class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenRefresh(BaseModel):
    refresh_token: str

# Document Management Schemas
class DocumentResponse(BaseModel):
    id: int
    document_id: str
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    status: IngestionStatus
    chunk_count: int
    total_characters: int
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    processing_time_ms: Optional[int]
    
    @validator('error_message')
    def clean_error_message(cls, v):
        if v is not None:
            from app.core.text_utils import truncate_error_message
            return truncate_error_message(v)
        return v

class DocumentUploadResponse(BaseModel):
    document_id: str = Field(..., description="ID to poll for ingestion status")
    message: str = "Document uploaded successfully"

class BulkDocumentUploadResponse(BaseModel):
    total_files: int = Field(..., description="Total number of files in the bulk upload")
    successful_uploads: int = Field(..., description="Number of files successfully uploaded and processed")
    failed_uploads: int = Field(..., description="Number of files that failed to upload or process")
    file_format: str = Field(..., description="The format of all uploaded files (e.g., .pdf, .docx, .txt)")
    uploaded_documents: List[Dict[str, str]] = Field(..., description="List of successfully uploaded documents with their IDs")
    failed_files: List[Dict[str, str]] = Field(..., description="List of failed files with error messages")
    message: str = Field(..., description="Summary message of the bulk upload operation")

# Bulk Upload Schemas (NEW)
class BulkUploadResponseItem(BaseModel):
    id: int
    filename: str
    status: str
    file_size: Optional[int] = None
    error_message: Optional[str] = None

class BulkUploadResponse(BaseModel):
    documents: List[BulkUploadResponseItem]
    total_uploaded: int
    successful_count: int
    failed_count: int

# Folder Upload Schemas (NEW)
class FolderUploadRequest(BaseModel):
    folder_path: str = Field(..., description="Absolute path to the folder containing documents to process")

class FolderUploadResponse(BaseModel):
    folder_path: str
    total_files_found: int
    total_files_processed: int
    documents: List[BulkUploadResponseItem]
    successful_count: int
    failed_count: int
    skipped_count: int
    processing_errors: List[Dict[str, str]] = []

# Query Schemas
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, alias="question")
    limit: int = Field(default=5, ge=1, le=20)
    include_history: bool = Field(default=True)
    session_id: Optional[str] = None
    max_results: Optional[int] = Field(default=8, ge=1, le=50)
    include_metadata: bool = Field(default=False)

class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    session_id: Optional[str] = None
    response_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    history_included: bool = False

class QueryHistoryResponse(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime
    response_time_ms: Optional[int]
    tokens_used: Optional[int]
    session_id: Optional[str]

# Citation and Context Schemas (NEW)
class Citation(BaseModel):
    snippet: str
    file_name: str = "Unknown Document"  # Provide default to prevent validation errors
    document_id: Optional[Union[int, str]] = None
    page: Optional[int] = None
    score: float

# Session Management
class SessionCreateResponse(BaseModel):
    session_id: str
    created_at: datetime

class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime
    last_activity: datetime
    query_count: int

class SessionUpdateRequest(BaseModel):
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Status and Health
class StatusResponse(BaseModel):
    document_id: str
    stage: str
    created_at: datetime
    updated_at: datetime
    progress: Optional[float] = None
    error_message: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    processing_details: Optional[Dict[str, Any]] = None

class SessionListResponse(BaseModel):
    sessions: List[Dict[str, Any]]

class DocumentListResponse(BaseModel):
    documents: List[Dict[str, Any]]

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float
    checks: Dict[str, bool]

# Error Responses
class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: datetime
    request_id: Optional[str] = None

class ValidationErrorResponse(BaseModel):
    error: str = "Validation Error"
    details: List[Dict[str, Any]]
    timestamp: datetime

# Search and Discovery
class SearchFilters(BaseModel):
    content_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    status: Optional[IngestionStatus] = None

class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    filters: Optional[SearchFilters] = None
    limit: int = Field(default=20, ge=1, le=100)

class DocumentSearchResponse(BaseModel):
    documents: List[DocumentResponse]
    total_count: int
    query: str
    search_time_ms: float
