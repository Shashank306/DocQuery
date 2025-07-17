# hybrid.py
"""
User-scoped hybrid retrieval combining dense vectors and BM25 keyword search.
All searches are filtered by user_id for proper data isolation.
"""
from typing import List, NamedTuple, Optional
from langchain_core.documents import Document
from app.core.logging import logger
from .vector_store import search_user_documents
from .keyword_index import bm25_search_user


class HybridSearchResult(NamedTuple):
    """Result from hybrid search with file metadata"""
    snippet: str
    score: float
    file_name: str
    document_id: Optional[str] = None
    page: Optional[int] = None
    chunk_id: Optional[str] = None


def hybrid_search_user_with_metadata(
    user_id: str,
    query: str, 
    k_dense: int = 10, 
    k_bm25: int = 10, 
    top_k: int = 8,
    dense_weight: float = 0.6,
    bm25_weight: float = 0.4
) -> List[HybridSearchResult]:
    """
    Perform hybrid search for a specific user with file metadata.
    
    Args:
        user_id: User ID to filter documents
        query: Search query
        k_dense: Number of results from vector search
        k_bm25: Number of results from BM25 search
        top_k: Final number of results to return
        dense_weight: Weight for dense vector scores
        bm25_weight: Weight for BM25 scores
        
    Returns:
        List of HybridSearchResult with file metadata
    """
    try:
        # Get results from both search methods
        dense_docs = search_user_documents(user_id, query, k_dense)
        bm25_docs = bm25_search_user(user_id, query, k_bm25)
        
        # Combine and rank results
        scored = {}
        
        # Score dense vector results
        for rank, doc in enumerate(dense_docs):
            doc_key = doc.page_content
            score = dense_weight * (1.0 / (rank + 1))
            
            # Extract metadata
            metadata = doc.metadata or {}
            result = HybridSearchResult(
                snippet=doc.page_content,
                score=score,
                file_name=metadata.get('file_name') or metadata.get('file_name', 'Unknown'),
                document_id = metadata.get('document_id') or 'Unknown',
                page=metadata.get('page'),
                chunk_id=metadata.get('chunk_id')
            )
            scored[doc_key] = result
        
        # Add BM25 results and combine scores for overlapping documents
        for rank, doc in enumerate(bm25_docs):
            doc_key = doc.page_content
            bm25_score = bm25_weight * (1.0 / (rank + 1))
            
            if doc_key in scored:
                # Document appears in both results - combine scores
                existing = scored[doc_key]
                scored[doc_key] = existing._replace(score=existing.score + bm25_score)
            else:
                # Document only in BM25 results
                metadata = doc.metadata or {}
                result = HybridSearchResult(
                    snippet=doc.page_content,
                    score=bm25_score,
                    file_name=metadata.get('filename') or metadata.get('file_name', 'Unknown'),
                    document_id=metadata.get('doc_id'),
                    page=metadata.get('page'),
                    chunk_id=metadata.get('chunk_id')
                )
                scored[doc_key] = result
        
        # Sort by combined score and return top results
        sorted_results = sorted(scored.values(), key=lambda x: x.score, reverse=True)
        final_results = sorted_results[:top_k]
        
        logger.info(f"Hybrid search for user {user_id}: {len(dense_docs)} dense + {len(bm25_docs)} BM25 = {len(final_results)} final results")
        return final_results
        
    except Exception as e:
        logger.error(f"Hybrid search failed for user {user_id}: {e}")
        return []

# Legacy function for backward compatibility (now requires user_id)
def hybrid_search(query: str, k_dense: int = 10, k_bm25: int = 10, top_k: int = 8) -> List[Document]:
    """
    Legacy hybrid search function.
    WARNING: This function is deprecated and should not be used in production.
    Use hybrid_search_user() instead to ensure proper user isolation.
    """
    logger.warning("Using deprecated hybrid_search function without user filtering!")
    
    # Import here to avoid circular imports in legacy code
    from .vector_store import get_vector_store
    from .keyword_index import bm25_search
    
    vs = get_vector_store()
    dense_docs = vs.similarity_search(query, k_dense)
    bm25_docs = bm25_search(query, k_bm25)

    # Simple ranking without user context
    scored = {}
    for rank, doc in enumerate(dense_docs):
        scored[doc.page_content] = (doc, 1.0 / (rank + 1))

    for rank, doc in enumerate(bm25_docs):
        if doc.page_content in scored:
            scored[doc.page_content] = (
                doc,
                scored[doc.page_content][1] + 1.0 / (rank + 1),
            )
        else:
            scored[doc.page_content] = (doc, 0.5 / (rank + 1))

    sorted_docs = sorted(scored.values(), key=lambda x: x[1], reverse=True)
    return [d for d, _ in sorted_docs[:top_k]]
