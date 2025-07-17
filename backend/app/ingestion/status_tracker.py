# status_tracker.py
"""
In-memory status tracker for document ingestion.
Simplified implementation without Redis dependency.
"""
from enum import Enum
from typing import Dict, Optional
import json
from datetime import datetime

class IngestionStage(str, Enum):
    QUEUED = "queued"
    LOADING = "loading"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETE = "complete"
    ERROR = "error"

# In-memory status storage (for simple single-process deployment)
# In production, this could be replaced with a database table
_status_store: Dict[str, Dict] = {}

def set_status(doc_id: str, stage: IngestionStage, progress: int = 0, error_message: Optional[str] = None) -> None:
    """Set document processing status in memory."""
    # Clean error message to prevent JSON serialization issues
    if error_message:
        from app.core.text_utils import truncate_error_message
        error_message = truncate_error_message(error_message)
    
    status_data = {
        "stage": stage.value,
        "progress": progress,
        "updated_at": datetime.utcnow().isoformat(),
        "error_message": error_message
    }
    _status_store[doc_id] = status_data

def get_status(doc_id: str) -> Optional[IngestionStage]:
    """Get document processing status."""
    status_data = _status_store.get(doc_id)
    if status_data:
        return IngestionStage(status_data["stage"])
    return None

def get_full_status(doc_id: str) -> Optional[Dict]:
    """Get full document processing status with progress."""
    status_data = _status_store.get(doc_id)
    if status_data:
        return {
            "stage": status_data.get("stage", ""),
            "progress": int(status_data.get("progress", 0)),
            "updated_at": status_data.get("updated_at", ""),
            "error_message": status_data.get("error_message") or None
        }
    return None
