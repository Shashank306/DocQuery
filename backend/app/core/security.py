# security.py
from typing import Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # More permissive CSP for Swagger UI to work
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:;",
        }
        
        # Add additional headers for production
        if settings.is_production:
            self.security_headers.update({
                "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
                "Cross-Origin-Embedder-Policy": "require-corp",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Resource-Policy": "cross-origin",
            })
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Skip strict security headers for docs endpoints to allow Swagger UI to work
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            # Only add basic security headers for docs
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-XSS-Protection"] = "1; mode=block"
        else:
            # Add all security headers for other endpoints
            for header, value in self.security_headers.items():
                response.headers[header] = value
        
        # Remove sensitive headers
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response

def validate_file_upload(
    filename: str, 
    content_type: str, 
    file_size: int
) -> Dict[str, Any]:
    """Validate uploaded file for security."""
    errors = []
    
    # Check file size
    if file_size > settings.MAX_FILE_SIZE:
        errors.append(f"File too large. Maximum size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB")
    
    # Check file extension
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    allowed_extensions = [ext.lstrip('.') for ext in settings.ALLOWED_FILE_TYPES]
    
    if file_ext not in allowed_extensions:
        errors.append(f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}")
    
    # Basic content type validation
    allowed_content_types = {
        'pdf': ['application/pdf'],
        'docx': [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/docx'
        ],
        'txt': ['text/plain'],
        'png': ['image/png'],
        'jpg': ['image/jpeg'],
        'jpeg': ['image/jpeg'],
    }
    
    if file_ext in allowed_content_types:
        if content_type not in allowed_content_types[file_ext]:
            errors.append(f"Content type mismatch for .{file_ext} file")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "sanitized_filename": sanitize_filename(filename)
    }

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for security."""
    import re
    
    # Remove path separators and other dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip(' .')
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = f"{name[:250]}.{ext}" if ext else filename[:255]
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    return filename
