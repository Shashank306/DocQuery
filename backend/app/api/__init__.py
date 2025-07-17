# Init file
from fastapi import APIRouter
from .endpoints import auth_simple as auth
from .endpoints import upload, sessions, query

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(upload.router, prefix="/upload", tags=["document-upload"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(query.router, prefix="/query", tags=["query"])

# Note: Full production endpoints temporarily disabled due to external dependencies
# These require PostgreSQL, and proper authentication setup:
# - upload endpoints (document upload and processing)
# - sessions endpoints (user session management)  
# - query endpoints (RAG query processing)
# - auth endpoints (user authentication)
#
# To enable them:
# 1. Set up PostgreSQL database  
# 2. Configure authentication properly
# 3. Update imports above to include the full endpoints
