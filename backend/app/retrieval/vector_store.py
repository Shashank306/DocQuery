# vector_store.py
"""
User-scoped Weaviate vector store implementation.
All documents are stored with user_id metadata for proper data isolation.
"""
import functools
import uuid
from typing import List, Optional, Dict, Any
import weaviate
from langchain_community.vectorstores import Weaviate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from app.core.config import settings
from app.core.logging import logger

# Export these functions for external use
__all__ = [
    'get_vector_store',
    'add_user_documents',
    'search_user_documents', 
    'delete_user_documents',
    'get_user_document_count',
    'reset_vector_store',
    'recreate_weaviate_schema',
    'force_recreate_schema'
]

# Global variable for lazy initialization
_embeddings_instance = None

def _embeddings() -> HuggingFaceEmbeddings:
    """Initialize embeddings with lazy loading"""
    global _embeddings_instance
    if _embeddings_instance is None:
        try:
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            _embeddings_instance = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={
                    'device': 'cpu',
                    'trust_remote_code': False
                },
                encode_kwargs={
                    'normalize_embeddings': True,
                    'batch_size': 1  # Process one at a time to avoid memory issues
                }
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _embeddings_instance

# Global variable for lazy client initialization
_client_instance = None

def _client() -> weaviate.Client:
    """Initialize Weaviate client using v3 API with lazy loading"""
    global _client_instance
    if _client_instance is None:
        try:
            logger.info(f"Connecting to Weaviate at {settings.WEAVIATE_URL}")
            
            # Weaviate v3 client initialization
            _client_instance = weaviate.Client(url=settings.WEAVIATE_URL)
            
            logger.info("Successfully connected to Weaviate v3")
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate v3: {e}")
            raise
    return _client_instance

# Global variable for lazy vector store initialization
_vector_store_instance = None

def get_vector_store() -> Weaviate:
    """Initialize vector store with lazy loading and minimal schema operations"""
    global _vector_store_instance
    if _vector_store_instance is None:
        try:
            client = _client()
            class_name = settings.WEAVIATE_CLASS
            logger.info(f"Initializing vector store with class: {class_name}")

            # Ensure schema exists but don't recreate if it already exists
            try:
                logger.info(f"Checking if Weaviate class exists: {class_name}")
                
                # Check if class exists by getting schema and checking class names
                schema = client.schema.get()
                existing_classes = {cls['class'] for cls in schema.get('classes', [])}
                
                # Only create if it doesn't exist
                if class_name not in existing_classes:
                    # Create the class with proper schema for user-scoped documents
                    client.schema.create_class({
                        "class": class_name,
                        "vectorizer": "none",  # External embeddings
                        "properties": [
                            {
                                "name": "text", 
                                "dataType": ["text"],
                                "description": "The text content"
                            },
                            {
                                "name": "user_id",
                                "dataType": ["text"],
                                "description": "User ID who owns this document"
                            },
                            {
                                "name": "doc_id",
                                "dataType": ["text"],
                                "description": "Document ID"
                            },
                            {
                                "name": "file_name",
                                "dataType": ["text"],
                                "description": "Original filename"
                            },
                            {
                                "name": "chunk_id",
                                "dataType": ["text"],
                                "description": "Chunk index within document"
                            }
                        ]
                    })
                    logger.info(f"Created Weaviate class: {class_name}")
                else:
                    logger.info(f"Weaviate class already exists: {class_name}")
            except Exception as e:
                logger.warning(f"Could not ensure schema exists: {e}")

            embeddings = _embeddings()
            
            _vector_store_instance = Weaviate(
                client=client,
                index_name=class_name,
                text_key="text",
                embedding=embeddings,
                by_text=False,
                attributes=["user_id", "doc_id", "file_name", "chunk_id", "page"]
            )
            
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    return _vector_store_instance

def add_user_documents(user_id: str, texts: List[str], doc_id: str, filename: str, page_numbers: Optional[List[int]] = None) -> List[str]:
    """
    Add documents to vector store with user_id metadata for proper data isolation.
    
    Args:
        user_id: User ID who owns these documents
        texts: List of text chunks to add
        doc_id: Document ID 
        filename: Original filename
        page_numbers: Optional list of page numbers for each chunk
        
    Returns:
        List of chunk IDs that were added
    """
    try:
        vector_store = get_vector_store()
        logger.info(f"Adding {len(texts)} chunks for user {user_id}, document {doc_id}")
        
        # Create metadata for each chunk
        metadatas = []
        chunk_ids = []
        
        for i, text in enumerate(texts):
            # Generate proper UUID for Weaviate
            chunk_uuid = str(uuid.uuid4())
            chunk_ids.append(chunk_uuid)
            
            metadata = {
                "user_id": user_id,
                "doc_id": doc_id,
                "filename": filename,
                "chunk_id": str(i),  # Store as string to match schema
                "chunk_uuid": chunk_uuid,
                "page": str(page_numbers[i]) if page_numbers and i < len(page_numbers) and page_numbers[i] is not None else None
            }
            metadatas.append(metadata)
        
        # Add texts with metadata to vector store
        vector_store.add_texts(
            texts=texts,
            metadatas=metadatas,
            ids=chunk_ids  # Use proper UUIDs
        )
        
        logger.info(f"Successfully added {len(chunk_ids)} chunks to vector store")
        return chunk_ids
        
    except Exception as e:
        logger.error(f"Failed to add documents to vector store: {e}")
        raise

def search_user_documents(user_id: str, query: str, k: int = 8) -> List[Document]:
    """
    Search documents for a specific user with proper data isolation.
    
    Args:
        user_id: User ID to search documents for
        query: Search query
        k: Number of results to return
        
    Returns:
        List of matching Document objects
    """
    try:
        vector_store = get_vector_store()
        logger.info(f"Searching documents for user {user_id} with query: {query[:50]}...")
        
        # Use where filter to ensure we only search the user's documents
        where_filter = {
            "path": ["user_id"],
            "operator": "Equal",
            "valueText": user_id
        }
        
        # Perform similarity search with user filter
        docs = vector_store.similarity_search(
            query=query,
            k=k,
            where=where_filter
        )
        # Add this line
        for d in docs:
            logger.info(f"Document metadata: {d.metadata}")

        logger.info(f"Found {len(docs)} matching documents for user {user_id}")
        return docs
        
    except Exception as e:
        logger.error(f"Failed to search user documents: {e}")
        return []

def delete_user_documents(user_id: str, doc_id: str) -> bool:
    """
    Delete all chunks for a specific document owned by a user.
    
    Args:
        user_id: User ID who owns the document
        doc_id: Document ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = _client()
        class_name = settings.WEAVIATE_CLASS
        
        logger.info(f"Deleting document {doc_id} for user {user_id}")
        
        # Delete all chunks for this document and user
        where_filter = {
            "operator": "And",
            "operands": [
                {
                    "path": ["user_id"],
                    "operator": "Equal", 
                    "valueText": user_id
                },
                {
                    "path": ["doc_id"],
                    "operator": "Equal",
                    "valueText": doc_id
                }
            ]
        }
        
        result = client.batch.delete_objects(
            class_name=class_name,
            where=where_filter
        )
        
        logger.info(f"Deleted document {doc_id} for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete document {doc_id} for user {user_id}: {e}")
        return False

def get_user_document_count(user_id: str) -> int:
    """
    Get the total number of chunks for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Number of chunks owned by the user
    """
    try:
        client = _client()
        class_name = settings.WEAVIATE_CLASS
        
        # Aggregate query to count user's documents
        result = client.query.aggregate(class_name).with_where({
            "path": ["user_id"],
            "operator": "Equal",
            "valueText": user_id
        }).with_meta_count().do()
        
        count = result['data']['Aggregate'][class_name][0]['meta']['count']
        logger.info(f"User {user_id} has {count} chunks")
        return count
        
    except Exception as e:
        logger.error(f"Failed to get document count for user {user_id}: {e}")
        return 0

def reset_vector_store():
    """Reset vector store instance - useful for testing or troubleshooting"""
    global _vector_store_instance, _client_instance, _embeddings_instance
    _vector_store_instance = None
    _client_instance = None
    _embeddings_instance = None
    logger.info("Reset all vector store instances")

def recreate_weaviate_schema():
    """Force recreation of Weaviate schema - use with caution as it deletes all data"""
    try:
        client = _client()
        class_name = settings.WEAVIATE_CLASS
        
        # Check if class exists and delete it
        schema = client.schema.get()
        existing_classes = {cls['class'] for cls in schema.get('classes', [])}
        
        if class_name in existing_classes:
            client.schema.delete_class(class_name)
            logger.info(f"Deleted existing class: {class_name}")
        
        # Reset vector store to force recreation
        global _vector_store_instance
        _vector_store_instance = None
        
        # Trigger recreation
        get_vector_store()
        logger.info("Successfully recreated Weaviate schema")
        
    except Exception as e:
        logger.error(f"Failed to recreate schema: {e}")
        raise

def force_recreate_schema():
    """Force recreation of Weaviate schema with updated properties"""
    try:
        client = _client()
        class_name = settings.WEAVIATE_CLASS
        
        logger.info(f"Force recreating schema for class: {class_name}")
        
        # Check if class exists and delete it
        try:
            schema = client.schema.get()
            existing_classes = {cls['class'] for cls in schema.get('classes', [])}
            
            if class_name in existing_classes:
                client.schema.delete_class(class_name)
                logger.info(f"Deleted existing class: {class_name}")
        except Exception as e:
            logger.warning(f"Could not delete existing class: {e}")
        
        # Create the class with updated schema
        client.schema.create_class({
            "class": class_name,
            "vectorizer": "none",  # External embeddings
            "properties": [
                {
                    "name": "text", 
                    "dataType": ["text"],
                    "description": "The text content"
                },
                {
                    "name": "user_id",
                    "dataType": ["text"],
                    "description": "User ID who owns this document"
                },
                {
                    "name": "doc_id",
                    "dataType": ["text"],
                    "description": "Document ID"
                },
                {
                    "name": "filename",
                    "dataType": ["text"],
                    "description": "Original filename"
                },
                {
                    "name": "chunk_id",
                    "dataType": ["text"],
                    "description": "Chunk index within document"
                }
            ]
        })
        logger.info(f"Created new class with updated schema: {class_name}")
        
        # Reset vector store to force recreation
        global _vector_store_instance
        _vector_store_instance = None
        
        logger.info("Successfully recreated Weaviate schema with updated properties")
        
    except Exception as e:
        logger.error(f"Failed to force recreate schema: {e}")
        raise

# Legacy function for backward compatibility
def get_vector_store_legacy():
    """Legacy function - use get_vector_store() instead"""
    logger.warning("Using legacy get_vector_store_legacy function")
    return get_vector_store()
