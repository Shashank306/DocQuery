# keyword_index.py
"""
User-scoped keyword search using Weaviate's BM25.
All searches are filtered by user_id for proper data isolation.
"""
from typing import List
from langchain_core.documents import Document
from app.core.config import settings
from .vector_store import _client
from app.core.logging import logger

def bm25_search_user(user_id: str, query: str, k: int = 10) -> List[Document]:
    """BM25 search for a specific user only."""
    try:
        client = _client()
        class_name = settings.WEAVIATE_CLASS
        
        result = (
            client.query
            .get(class_name, ["text", "doc_id", "user_id", "chunk_id", "filename"])
            .with_bm25(query, properties=["text"])
            .with_where({
                "path": ["user_id"],
                "operator": "Equal",
                "valueText": user_id
            })
            .with_limit(k)
            .do()
        )
        
        documents = []
        if "data" in result and "Get" in result["data"] and class_name in result["data"]["Get"]:
            for hit in result["data"]["Get"][class_name]:
                doc = Document(
                    page_content=hit["text"],
                    metadata={
                        "doc_id": hit["doc_id"],
                        "user_id": hit["user_id"],
                        "chunk_id": hit["chunk_id"],
                        "filename": hit["filename"]
                    }
                )
                documents.append(doc)
        
        logger.info(f"BM25 search found {len(documents)} documents for user {user_id}")
        return documents
        
    except Exception as e:
        logger.error(f"BM25 search failed for user {user_id}: {e}")
        return []

# Legacy function for backward compatibility (now requires user_id)
def bm25_search(query: str, k: int = 10) -> List[Document]:
    """
    Legacy BM25 search function.
    WARNING: This function is deprecated and should not be used in production.
    Use bm25_search_user() instead to ensure proper user isolation.
    """
    logger.warning("Using deprecated bm25_search function without user filtering!")
    client = _client()
    class_name = settings.WEAVIATE_CLASS
    
    result = (
        client.query
        .get(class_name, ["text", "doc_id"])
        .with_bm25(query, properties=["text"])
        .with_limit(k)
        .do()
    )
    
    return [
        Document(
            page_content=hit["text"], 
            metadata={"doc_id": hit["doc_id"]}
        )
        for hit in result["data"]["Get"][class_name]
    ]
