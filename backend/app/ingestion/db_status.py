# db_status.py
from typing import Optional
from app.models.db import UserDocument, IngestionStatus
from app.core.database import get_session
from sqlmodel import select

def update_document_status(
    document_id: str, 
    status: IngestionStatus, 
    error_message: Optional[str] = None,
    chunk_count: Optional[int] = None,
    total_characters: Optional[int] = None,
    processing_time_ms: Optional[int] = None
):
    """Update document processing status in database."""
    try:
        with get_session() as session:
            document = session.exec(
                select(UserDocument).where(UserDocument.document_id == document_id)
            ).first()
            if document:
                document.status = status
                if error_message:
                    document.error_message = error_message
                if chunk_count is not None:
                    document.chunk_count = chunk_count
                if total_characters is not None:
                    document.total_characters = total_characters
                if processing_time_ms is not None:
                    document.processing_time_ms = processing_time_ms
                session.add(document)
                session.commit()
    except Exception as e:
        # Log or handle DB update errors as needed
        pass
