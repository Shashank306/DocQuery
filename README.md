# RAG Hybrid FastAPI Backend

A production-ready Retrieval-Augmented Generation (RAG) system with user authentication, document processing, and hybrid search capabilities.

## 🏗️ **Project Architecture**
## Code Structure

```
app/
├── __init__.py
├── main.py              # FastAPI application entry point with middleware
├── worker.py            # RQ background worker for document processing
├── auth/
│   ├── __init__.py
│   ├── security.py      # JWT authentication & password hashing
│   └── dependencies.py  # Auth dependencies for protected routes
├── api/
│   ├── __init__.py
│   └── endpoints/
│       ├── __init__.py
│       ├── auth.py      # User signup/login endpoints
│       ├── query.py     # Protected query endpoints with user context
│       ├── upload.py    # Protected upload with user association
│       └── status.py    # Document processing status
├── core/
│   ├── __init__.py
│   ├── config.py        # Application configuration with secrets
│   ├── database.py      # SQLModel database setup with connection pooling
│   ├── logging.py       # Structured logging configuration
│   └── security.py      # Security middleware and utilities
├── ingestion/
│   ├── __init__.py
│   ├── chunker.py       # Text chunking with configurable strategies
│   ├── document_loader.py # Multi-format document loading with validation
│   ├── ocr.py          # OCR processing with error handling
│   ├── pipeline.py     # User-scoped ingestion pipeline
│   └── status_tracker.py # Ingestion status tracking in Redis
├── llm/
│   ├── __init__.py
│   └── chat.py         # GROQ LLM integration with error handling
├── models/
│   ├── __init__.py
│   ├── db.py           # SQLModel database models (User, QueryLog, etc.)
│   └── schemas.py      # Pydantic API request/response schemas
├── retrieval/
│   ├── __init__.py
│   ├── hybrid.py       # User-scoped hybrid search implementation
│   ├── keyword_index.py # BM25 search with user filtering
│   └── vector_store.py # Weaviate operations with user isolation
```

## Key Features

### User Authentication & Authorization
- JWT-based authentication with refresh tokens
- Secure password hashing with bcrypt
- Role-based access control (User/Admin)
- Rate limiting on auth endpoints

### Multi-Tenant Data Isolation
- All documents tagged with user_id in Weaviate
- Database queries filtered by user context
- User-scoped search and retrieval
- Complete data separation between users

### Production Security
- CORS configuration for web frontends
- Security headers middleware
- File upload validation and size limits
- Input sanitization and validation

### Scalable Architecture
- Background workers for document processing
- Connection pooling for database efficiency
- Redis-based task queue with RQ
- Horizontal scaling with multiple workers

### Observability
- Structured logging with correlation IDs
- Prometheus metrics for monitoring
- Health checks for all services
- Request/response timing and tracing

## Development


## Production Deployment

### Environment Variables

Key environment variables for production:

```bash
# Security
SECRET_KEY="your-production-secret-key"
ENVIRONMENT="production"

# Database
DATABASE_URL="postgresql://user:pass@postgres:5432/rag_db"

# APIs
GROQ_API_KEY="your-groq-api-key"
WEAVIATE_API_KEY="your-weaviate-api-key"


# CORS
BACKEND_CORS_ORIGINS="https://yourdomain.com"
```

### Docker Deployment

```bash
# Build and deploy
docker-compose -f docker-compose.yml up -d

# Check logs
docker-compose logs -f api

# Scale workers
docker-compose up -d --scale worker=4
```

### Health Monitoring

- **API Health**: `GET /health`
- **Database**: PostgreSQL connection check
- **Vector DB**: Weaviate ready check

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## 🚀 Running the Application

### Start the Server
```bash
# Method 1: Direct uvicorn command
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Method 2: Using Python module
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Test Document Status Endpoints

1. **Access Swagger UI**: http://localhost:8000/docs
2. **Create Test Document**: Use `POST /status/test-document`
3. **Check Status**: Use `GET /status/{document_id}` with returned ID
4. **Monitor Progress**: Track processing through stages (queued → loading → chunking → embedding → storing → complete)

## 📄 License

This project is licensed under the MIT License.
---
**The RAG Hybrid system provides a complete, production-ready solution for document processing, vector search, and AI-powered question answering with user authentication and real-time status tracking.**
