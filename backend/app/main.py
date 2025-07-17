# main.py
import time
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging, logger
from app.core.security import SecurityHeadersMiddleware
from app.core.text_utils import clean_text_for_json
from app.api import api_router
from app.models.schemas import ErrorResponse, ValidationErrorResponse
from datetime import datetime, timezone

# Custom JSON encoder to handle special characters and datetime objects
class SafeJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        if isinstance(content, dict):
            # Clean any string values in the content
            cleaned_content = self._clean_dict(content)
        else:
            cleaned_content = content
        
        return json.dumps(
            cleaned_content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(',', ':'),
            default=self._json_serializer,
        ).encode('utf-8')
    
    def _clean_dict(self, d):
        """Recursively clean dictionary values"""
        if isinstance(d, dict):
            return {k: self._clean_dict(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [self._clean_dict(item) for item in d]
        elif isinstance(d, str):
            return clean_text_for_json(d)
        else:
            return d
    
    def _json_serializer(self, obj):
        """Handle objects that aren't JSON serializable by default"""
        from datetime import datetime, date
        
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            # Handle other objects by converting to dict
            return obj.__dict__
        else:
            # For any other type, convert to string
            return str(obj)

# Setup structured logging
setup_logging()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Application startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting User Authentication RAG Service...")
    
    try:
        # Skip database initialization for now to avoid hanging
        # try:
        #     init_db()
        #     logger.info("Database initialized successfully")
        # except Exception as db_error:
        #     logger.warning(f"Database initialization skipped: {db_error}")
        #     logger.info("Running without database functionality")
        
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down User Authentication RAG Service...")

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Production-ready RAG system with user authentication and per-user data isolation",
    docs_url="/docs",      # Always enable docs for now
    redoc_url="/redoc",    # Always enable redoc for now
    openapi_url="/openapi.json",  # Always enable OpenAPI spec
    lifespan=lifespan,
    default_response_class=SafeJSONResponse
)

# Security Middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY
)

# CORS Middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

# Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time,
    )
    
    return response

# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url),
        method=request.method,
    )
    return SafeJSONResponse(
        content=ErrorResponse(
            error="HTTP Error",
            detail=clean_text_for_json(str(exc.detail)),
            timestamp=datetime.now(timezone.utc)
        ).model_dump(),
        status_code=exc.status_code
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation error",
        errors=exc.errors(),
        url=str(request.url),
        method=request.method,
    )
    return SafeJSONResponse(
        content=ValidationErrorResponse(
            details=exc.errors(),
            timestamp=datetime.now(timezone.utc)
        ).model_dump(),
        status_code=422
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        url=str(request.url),
        method=request.method,
        exc_info=True,
    )
    return SafeJSONResponse(
        content=ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred",
            timestamp=datetime.now(timezone.utc)
        ).model_dump(),
        status_code=500
    )

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)

# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "environment": settings.ENVIRONMENT
    }

# Remove deprecated startup event - functionality moved to lifespan handler

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        reload_dirs=["app"]  # Only watch the app directory for reloads
    )
