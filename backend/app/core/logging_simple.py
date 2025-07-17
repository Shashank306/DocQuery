# logging_simple.py
"""
Simplified logging configuration without external dependencies.
"""
import logging
import sys
from typing import Any, Dict

def setup_logging() -> None:
    """Configure basic logging for the application."""
    # Close all existing handlers before clearing
    for handler in logging.getLogger().handlers:
        try:
            handler.close()
        except Exception:
            pass
    logging.getLogger().handlers.clear()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log', mode='a', encoding='utf-8')
        ],
        force=True
    )

# Create logger instance
logger = logging.getLogger("rag_hybrid")

def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance."""
    if name:
        return logging.getLogger(f"rag_hybrid.{name}")
    return logger

# Setup logging when module is imported
setup_logging()
