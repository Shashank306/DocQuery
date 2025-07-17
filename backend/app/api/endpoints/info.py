# info.py
"""
API information and system status endpoints (no auth required)
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/info", tags=["api-info"])

@router.get("/", summary="API Information")
async def get_api_info():
    """Get basic API information and available features."""
    return {
        "api_name": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "api_prefix": settings.API_PREFIX,
        "timestamp": datetime.now(timezone.utc),
        "features": {
            "document_processing": True,
            "status_tracking": True,
            "health_checks": True,
            "authentication": "Available (not configured in demo)",
            "vector_search": "Available (Weaviate integration)",
            "llm_integration": "Available (GROQ integration)"
        },
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc", 
            "openapi": "/openapi.json",
            "health": "/api/v1/health/health/live",
            "status": "/api/v1/status/{document_id}"
        }
    }

@router.get("/capabilities", summary="System Capabilities")
async def get_capabilities():
    """Get detailed system capabilities and configuration."""
    return {
        "document_processing": {
            "max_file_size_mb": settings.MAX_FILE_SIZE // (1024 * 1024),
            "supported_types": settings.ALLOWED_FILE_TYPES,
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP
        },
        "vector_search": {
            "embedding_model": settings.EMBEDDING_MODEL,
            "vector_store": "Weaviate",
            "default_search_limit": settings.DEFAULT_SEARCH_LIMIT,
            "max_search_limit": settings.MAX_SEARCH_LIMIT
        },
        "llm": {
            "provider": "GROQ",
            "model": settings.GROQ_MODEL,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "temperature": settings.LLM_TEMPERATURE
        },
        "rate_limits": {
            "upload": settings.RATE_LIMIT_UPLOAD,
            "query": settings.RATE_LIMIT_QUERY
        }
    }

@router.get("/version", summary="Version Information")
async def get_version():
    """Get version and build information."""
    return {
        "version": settings.VERSION,
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_path": "/api/v1",
        "status": "operational"
    }
