"""
Text utilities for cleaning and sanitizing text content.
"""
import re
import json
from typing import Optional

def clean_text_for_json(text: Optional[str]) -> Optional[str]:
    """
    Clean text to make it safe for JSON serialization.
    Removes or escapes control characters that could cause JSON parsing errors.
    
    Args:
        text: The text to clean
        
    Returns:
        Cleaned text safe for JSON, or None if input was None
    """
    if text is None:
        return None
    
    if not isinstance(text, str):
        text = str(text)
    
    # Remove or replace problematic control characters
    # Keep common whitespace (space, tab, newline) but escape them properly
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Ensure the text can be JSON serialized
    try:
        json.dumps(text)
        return text
    except (TypeError, ValueError):
        # If it still can't be serialized, escape it more aggressively
        return text.encode('unicode_escape').decode('ascii')

def truncate_error_message(error_msg: Optional[str], max_length: int = 500) -> Optional[str]:
    """
    Truncate error message to prevent overly long responses.
    
    Args:
        error_msg: Error message to truncate
        max_length: Maximum length allowed
        
    Returns:
        Truncated and cleaned error message
    """
    if error_msg is None:
        return None
    
    # Clean the error message first
    cleaned = clean_text_for_json(error_msg)
    
    if cleaned and len(cleaned) > max_length:
        return cleaned[:max_length-3] + "..."
    
    return cleaned

def safe_str(obj) -> str:
    """
    Safely convert any object to string, handling special characters.
    
    Args:
        obj: Object to convert to string
        
    Returns:
        Safe string representation
    """
    try:
        from datetime import datetime, date
        
        # Handle datetime objects specially
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        
        text = str(obj)
        return clean_text_for_json(text) or ""
    except Exception:
        return "[Unable to convert to string]"

def safe_json_serializable(obj):
    """
    Convert any object to a JSON-serializable format.
    
    Args:
        obj: Object to make JSON serializable
        
    Returns:
        JSON-serializable representation
    """
    from datetime import datetime, date
    
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: safe_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_serializable(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return safe_json_serializable(obj.__dict__)
    else:
        return safe_str(obj)
