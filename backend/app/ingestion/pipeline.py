# pipeline.py
"""
User-scoped end-to-end ingestion pipeline.
All documents are associated with a user_id for proper data isolation.
Runs in RQ background workers for scalability.
"""
import uuid
from pathlib import Path
from typing import Tuple, Callable

from app.core.logging import logger
from app.ingestion.document_loader import extract_text
from app.ingestion.chunker import chunk_text
from app.ingestion.status_tracker import IngestionStage, set_status
from app.ingestion.db_status import update_document_status
from app.retrieval.vector_store import add_user_documents
from app.models.db import IngestionStatus

def ingest_file_for_user(user_id: str, path: Path, filename: str, document_id: str = None) -> Tuple[str, Callable]:
    """
    Ingest a file for a specific user and return the document_id and task function.
    
    Args:
        user_id: User ID to associate the document with
        path: Path to the file to ingest
        filename: Original filename for metadata
        document_id: Optional document ID to use (if not provided, generates new one)
        
    Returns:
        Tuple of (document_id, task_function)
    """
    doc_id = document_id or uuid.uuid4().hex
    logger.info(f"Enqueued {filename} as {doc_id} for user {user_id}")
    set_status(doc_id, IngestionStage.QUEUED)
    update_document_status(doc_id, IngestionStatus.QUEUED)

    def _run() -> None:
        """Task function that runs in the background worker."""
        try:
            logger.info(f"Starting ingestion for document {doc_id} (user: {user_id})")
            
            # Load document
            set_status(doc_id, IngestionStage.LOADING, progress=10)
            update_document_status(doc_id, IngestionStatus.PROCESSING)
            logger.info(f"Loading document {doc_id}")
            text = extract_text(path)
            if not text or not isinstance(text, str) or text.strip() == "":
                logger.error(f"No text extracted from document {doc_id}. Aborting ingestion.")
                set_status(doc_id, IngestionStage.ERROR, progress=0, error_message="No text extracted from document.")
                return
            logger.info(f"Document {doc_id} loaded, text length: {len(text)}")

            # Chunk text
            set_status(doc_id, IngestionStage.CHUNKING, progress=30)
            update_document_status(doc_id, IngestionStatus.PROCESSING)
            logger.info(f"Chunking document {doc_id}")
            chunks = chunk_text(text)
            if not chunks or not isinstance(chunks, list) or all((c is None or str(c).strip() == "") for c in chunks):
                logger.error(f"No valid chunks generated for document {doc_id}. Aborting ingestion.")
                set_status(doc_id, IngestionStage.ERROR, progress=0, error_message="No valid chunks generated from document.")
                return
            logger.info(f"Document {doc_id} chunked into {len(chunks)} pieces")

            # Store in vector database with user context
            set_status(doc_id, IngestionStage.EMBEDDING, progress=50)
            update_document_status(doc_id, IngestionStatus.PROCESSING)
            logger.info(f"Adding chunks to vector store for document {doc_id}")
            
            chunk_ids = add_user_documents(
                user_id=user_id,
                texts=chunks,
                doc_id=doc_id,
                filename=filename
            )
            
            logger.info(f"Successfully added {len(chunk_ids)} chunks to vector store for document {doc_id}")

            set_status(doc_id, IngestionStage.STORING, progress=90)
            update_document_status(doc_id, IngestionStatus.PROCESSING)
            # BM25 keyword index is auto-built by Weaviate

            set_status(doc_id, IngestionStage.COMPLETE, progress=100)
            update_document_status(doc_id, IngestionStatus.COMPLETED)
            logger.info(f"Document {doc_id} ingested successfully for user {user_id} ({len(chunks)} chunks)")
            
        except Exception as exc:
            logger.exception(f"Ingestion failed for {doc_id} (user: {user_id}): {exc}")
            
            # Clean error message to prevent JSON issues
            from app.core.text_utils import truncate_error_message
            clean_error = truncate_error_message(str(exc))
            
            set_status(doc_id, IngestionStage.ERROR, progress=0, error_message=clean_error)
            update_document_status(doc_id, IngestionStatus.FAILED, error_message=clean_error)
        finally:
            # Clean up the temporary file
            try:
                if path.exists():
                    path.unlink()
                    logger.info(f"Cleaned up temporary file: {path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {path}: {e}")

    return doc_id, _run

# Legacy function for backward compatibility
def ingest_file(path: Path) -> Tuple[str, Callable]:
    """
    Legacy ingestion function for backward compatibility.
    WARNING: This function is deprecated and should not be used in production.
    Use ingest_file_for_user() instead to ensure proper user isolation.
    """
    logger.warning("Using deprecated ingest_file function without user context!")
    
    doc_id = uuid.uuid4().hex
    logger.info("Enqueued %s as %s", path.name, doc_id)
    set_status(doc_id, IngestionStage.QUEUED)

    def _run() -> None:
        try:
            logger.info("Starting ingestion for document %s", doc_id)
            
            set_status(doc_id, IngestionStage.LOADING)
            logger.info("Loading document %s", doc_id)
            text = extract_text(path)
            if not text or not isinstance(text, str) or text.strip() == "":
                logger.error(f"No text extracted from document {doc_id}. Aborting ingestion.")
                set_status(doc_id, IngestionStage.ERROR, progress=0, error_message="No text extracted from document.")
                return
            logger.info("Document %s loaded, text length: %d", doc_id, len(text))

            set_status(doc_id, IngestionStage.CHUNKING)
            logger.info("Chunking document %s", doc_id)
            chunks = chunk_text(text)
            if not chunks or not isinstance(chunks, list) or all((c is None or str(c).strip() == "") for c in chunks):
                logger.error(f"No valid chunks generated for document {doc_id}. Aborting ingestion.")
                set_status(doc_id, IngestionStage.ERROR, progress=0, error_message="No valid chunks generated from document.")
                return
            logger.info("Document %s chunked into %d pieces", doc_id, len(chunks))

            set_status(doc_id, IngestionStage.EMBEDDING)
            logger.info("Initializing vector store for document %s", doc_id)
            
            # Use legacy vector store method
            from app.retrieval.vector_store import get_vector_store
            vs = get_vector_store()
            logger.info("Vector store ready, adding texts for document %s", doc_id)
            
            ids = [str(uuid.uuid4()) for _ in range(len(chunks))]
            metadatas = [{"doc_id": doc_id, "chunk_id": i} for i in range(len(chunks))]
            vs.add_texts(texts=chunks, ids=ids, metadatas=metadatas)
            logger.info("Successfully added %d chunks to vector store for document %s", len(chunks), doc_id)

            set_status(doc_id, IngestionStage.STORING)
            set_status(doc_id, IngestionStage.COMPLETE)
            logger.info("Document %s ingested successfully (%d chunks)", doc_id, len(chunks))
            
        except Exception as exc:
            logger.exception("Ingestion failed for %s: %s", doc_id, exc)
            set_status(doc_id, IngestionStage.ERROR)

    return doc_id, _run
