# query.py
"""
User-authenticated query endpoints for RAG system with history support.
All queries are scoped to the authenticated user's documents.
"""
import time
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlmodel import Session, select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import get_session
from app.core.logging_simple import logger
from app.auth.dependencies import get_current_user
from app.models.db import User, UserQuery
from app.models.schemas import (
    QueryRequest, 
    QueryResponse, 
    QueryHistoryResponse,
    Citation
)
from app.retrieval.hybrid import hybrid_search_user_with_metadata, HybridSearchResult
from app.llm.chat import generate_response_with_history

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["query"])

@router.post("/search", response_model=QueryResponse)
@limiter.limit(settings.RATE_LIMIT_QUERY)
async def query_search(
    request: Request,
    query_request: QueryRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Ask a question using the user's uploaded documents with history support."""
    start_time = time.time()
    
    try:
        logger.info(f"Processing query for user {current_user.username}: {query_request.query[:100]}...")
        
        # Step 1: Retrieve context from vector store
        search_results = hybrid_search_user_with_metadata(
            user_id=str(current_user.id),
            query=query_request.query,
            top_k=query_request.limit,
        )

        
        # Step 2: Build conversation history if requested
        history: List[tuple[str, str]] = []
        if query_request.include_history:
            # If session_id is provided, get history from that session only
            if query_request.session_id:
                stmt = (
                    select(UserQuery)
                    .where(
                        UserQuery.user_id == current_user.id,
                        UserQuery.session_id == query_request.session_id
                    )
                    .order_by(UserQuery.created_at.desc())
                    .limit(settings.HISTORY_TURNS)
                )
            else:
                # Get general history for the user
                stmt = (
                    select(UserQuery)
                    .where(UserQuery.user_id == current_user.id)
                    .order_by(UserQuery.created_at.desc())
                    .limit(settings.HISTORY_TURNS)
                )
            
            last_queries = session.exec(stmt).all()
            # Reverse to get chronological order (oldest to newest)
            last_queries = list(reversed(last_queries))
            history = [(q.question, q.answer or "") for q in last_queries]
            
            # Debug logging for conversation history
            logger.info(f"Including {len(history)} conversation turns in context for user {current_user.id}")
            if history:
                logger.info(f"History preview: {[q for q, a in history[-2:]]}")  # Log last 2 questions
        
        # Step 3: Generate response with context and history
        if not search_results:
            answer = "I don't have any relevant documents to answer your question. Please upload some documents first."
            tokens_used = 0
            citations = []
        else:
            # Format context for LLM
            context = "\n".join([r.snippet for r in search_results])
            
            # Generate response using GROQ with history
            llm_response = generate_response_with_history(
                context=context,
                question=query_request.query,
                history=history if query_request.include_history else None,
                user_id=str(current_user.id)
            )
            
            answer = llm_response["answer"]
            tokens_used = llm_response["usage"]["total_tokens"]
            
            # Prepare citations with file metadata and handle None values
            citations = [
                Citation(
                    snippet=r.snippet,
                    file_name=r.file_name or "Unknown Document",
                    document_id=r.document_id,
                    page=r.page,
                    score=r.score
                )
                for r in search_results
            ]
        
        # Step 4: Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Step 5: Save this query to database
        user_query = UserQuery(
            user_id=current_user.id,
            session_id=query_request.session_id,
            question=query_request.query,
            answer=answer,
            context_used="\n".join([r.snippet for r in search_results]),
            response_time_ms=response_time_ms,
            tokens_used=tokens_used
        )
        
        session.add(user_query)
        # Auto-set session name if it's the first message and name is missing
        if query_request.session_id:
            from app.models.db import UserSession
            user_session = session.exec(
                select(UserSession).where(UserSession.session_id == query_request.session_id)
            ).first()
            if user_session and not user_session.name:
                user_session.name = query_request.query.strip()[:50]

        session.commit()
        
        logger.info(f"Query completed for user {current_user.username} in {response_time_ms}ms")
        
        return QueryResponse(
            answer=answer,
            citations=citations,
            session_id=query_request.session_id,
            response_time_ms=response_time_ms,
            tokens_used=tokens_used,
            history_included=query_request.include_history
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query processing error for user {current_user.id}: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query processing failed"
        )

@router.get("/history", response_model=List[QueryHistoryResponse])
async def get_query_history(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 50
):
    """Get user's query history."""
    try:
        from sqlmodel import select
        
        query = (
            select(UserQuery)
            .where(UserQuery.user_id == current_user.id)
            .offset(skip)
            .limit(limit)
            .order_by(UserQuery.created_at.desc())
        )
        
        queries = session.exec(query).all()
        
        return [
            QueryHistoryResponse(
                id=q.id,
                question=q.question,
                answer=q.answer,
                created_at=q.created_at,
                response_time_ms=q.response_time_ms,
                tokens_used=q.tokens_used,
                session_id=q.session_id
            )
            for q in queries
        ]
        
    except Exception as e:
        logger.error(f"Failed to get query history for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve query history"
        )
