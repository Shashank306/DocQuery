# logging.py
import logging
import sys
from typing import Any, Dict
from logging.config import dictConfig
import structlog
from structlog.stdlib import LoggerFactory
from app.core.config import settings

def setup_logging() -> None:
    """Configure structured logging for the application."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.is_production 
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "structured": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer()
                if settings.is_production
                else structlog.dev.ConsoleRenderer(),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structured" if settings.is_production else "default",
                "stream": sys.stdout,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": settings.LOG_LEVEL,
        },
        "loggers": {
            # Suppress verbose logs from dependencies
            "uvicorn.access": {
                "level": "WARNING",
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "propagate": False,
            },
            "weaviate": {
                "level": "WARNING",
                "propagate": False,
            },
        },
    }
    
    dictConfig(log_config)

# Get structured logger
logger = structlog.get_logger(settings.APP_NAME)

class RequestContextFilter(logging.Filter):
    """Add request context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add request ID if available
        record.request_id = getattr(record, 'request_id', None)
        return True

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger for a specific module."""
    return structlog.get_logger(name)

def log_function_call(func_name: str, **kwargs: Any) -> None:
    """Log function call with parameters."""
    logger.debug(
        "Function called",
        function=func_name,
        parameters=kwargs
    )

def log_performance(operation: str, duration_ms: float, **metadata: Any) -> None:
    """Log performance metrics."""
    logger.info(
        "Performance metric",
        operation=operation,
        duration_ms=duration_ms,
        **metadata
    )

def log_security_event(event_type: str, details: Dict[str, Any]) -> None:
    """Log security-related events."""
    logger.warning(
        "Security event",
        event_type=event_type,
        details=details
    )
