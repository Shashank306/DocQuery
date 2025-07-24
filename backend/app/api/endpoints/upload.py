# upload.py
"""
User-authenticated document upload endpoints with enhanced DirectoryLoader support.

Key Features:
- Multi-file type support: PDF, TXT, CSV, JSON (DOCX ready when dependency available)
- Enhanced DirectoryLoader with custom filtering and error handling
- Background processing with rich metadata preservation
- ZIP file extraction and validation
- User-specific document isolation
- Comprehensive error handling and logging
- Rate limiting and file size validation

All uploaded documents are associated with the authenticated user.
"""
import uuid
import zipfile
import tempfile
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, status, BackgroundTasks,Form
from sqlmodel import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders.json_loader import JSONLoader

from app.core.config import settings
from app.core.database import get_session
from app.core.logging_simple import logger
from app.auth.dependencies import get_current_user
from app.models.db import User, UserDocument, IngestionStatus
from app.models.schemas import DocumentUploadResponse, DocumentResponse, BulkDocumentUploadResponse, BulkUploadResponseItem, BulkUploadResponse, FolderUploadRequest, FolderUploadResponse
from app.ingestion.pipeline import ingest_file_for_user

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["document-upload"])

def validate_file(file: UploadFile) -> None:
    """Validate uploaded file."""
    if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )
    
    # Check file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}"
        )

def validate_files_same_format(files: List[UploadFile]) -> str:
    """Validate that all uploaded files are of the same format and return the format."""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    if len(files) > 20:  # Reasonable limit for bulk upload
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 files allowed per bulk upload"
        )
    
    first_file_ext = Path(files[0].filename).suffix.lower() if files[0].filename else None
    if not first_file_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First file has no extension"
        )
    
    for i, file in enumerate(files):
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File at position {i} has no filename"
            )
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext != first_file_ext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"All files must be of the same format. Expected {first_file_ext}, got {file_ext} at position {i}"
            )
        
        # Validate each file individually
        validate_file(file)
    
    return first_file_ext

def save_upload_file(file: UploadFile, user_id: int) -> Path:
    """Save uploaded file to user-specific directory."""
    user_dir = settings.DATA_DIR / f"user_{user_id}"
    user_dir.mkdir(exist_ok=True)
    
    # Generate unique filename while preserving extension
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    dest_path = user_dir / unique_filename
    
    try:
        with dest_path.open("wb") as dest_file:
            file.file.seek(0)  # Ensure we're at the beginning
            dest_file.write(file.file.read())
        
        logger.info(f"Saved file for user {user_id}: {dest_path}")
        return dest_path
        
    except Exception as e:
        logger.error(f"Failed to save file for user {user_id}: {e}")
        # Clean up partial file
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file"
        )

@router.post("", response_model=DocumentUploadResponse)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Upload a document for processing."""
    try:
        # Validate the uploaded file
        validate_file(file)
        
        # Save file to disk
        file_path = save_upload_file(file, current_user.id)
        
        # Create document record in database
        document_id = uuid.uuid4().hex
        file_size = file_path.stat().st_size
        
        user_document = UserDocument(
            user_id=current_user.id,
            document_id=document_id,
            filename=file_path.name,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            status=IngestionStatus.PROCESSING
        )
        
        session.add(user_document)
        session.commit()
        session.refresh(user_document)
        
        # Process document directly using ingestion pipeline
        try:
            # Get the document ID and task function from ingestion pipeline
            # Pass the same document_id we created to ensure status tracking works
            doc_id_returned, task_function = ingest_file_for_user(
                user_id=str(current_user.id),
                path=file_path,
                filename=file.filename,
                document_id=document_id  # Pass the same document_id
            )
            
            logger.info(f"Ingestion pipeline set up for document {doc_id_returned}, about to execute task")
            
            # Execute the task immediately (synchronous processing)
            task_function()
            logger.info(f"Task function completed for document {document_id}")
            
            # Check if the processing was actually successful
            from app.ingestion.status_tracker import get_full_status
            final_status = get_full_status(document_id)
            logger.info(f"Final status for document {document_id}: {final_status}")
            
        except Exception as e:
            logger.error(f"Failed to process document: {e}")
            logger.exception("Full error details:")
            
            # Clean error message to prevent JSON serialization issues
            from app.core.text_utils import truncate_error_message
            clean_error = truncate_error_message(str(e))
            
            # Update document status to failed
            user_document.status = IngestionStatus.FAILED
            user_document.error_message = clean_error
            session.add(user_document)
            session.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process document: {clean_error}"
            )
        
        logger.info(f"Document uploaded successfully by user {current_user.username}: {document_id}")
        
        return DocumentUploadResponse(
            document_id=document_id,
            message=f"Document '{file.filename}' uploaded successfully and queued for processing"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error for user {current_user.id}: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed"
        )


def _get_file_type_loaders() -> Dict[str, Dict[str, Any]]:
    """
    Get enhanced file type loaders configuration based on Medium article best practices.
    
    This implementation follows the DirectoryLoader best practices from:
    https://medium.com/towards-agi/how-to-load-multiple-file-types-with-directoryloader-in-langchain-2e933a7c6dc3
    
    Features:
    - Specific glob patterns for each file type
    - Custom loader configurations with optimized parameters
    - Error handling and encoding specifications
    - Metadata preservation for rich document processing
    """
    return {
        # PDF files - optimized for text extraction
        "**/*.pdf": {
            "name": "PDF Loader",
            "loader_class": PyPDFLoader,
            "kwargs": {
                "extract_images": False,  # Focus on text for RAG
            },
            "description": "Handles PDF documents with text extraction"
        },
        
        # Text files - with encoding auto-detection
        "**/*.txt": {
            "name": "Text Loader", 
            "loader_class": TextLoader,
            "kwargs": {
                "encoding": "utf-8",
                "autodetect_encoding": True
            },
            "description": "Handles plain text files with UTF-8 encoding"
        },
        
        
        # Note: DOCX support would require python-docx dependency
        # "**/*.docx": {
        #     "name": "DOCX Loader",
        #     "loader_class": Docx2txtLoader,
        #     "kwargs": {},
        #     "description": "Handles Microsoft Word documents"
        # }
    }


def _get_content_type(file_extension: str) -> str:
    """Get content type based on file extension."""
    content_types = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".csv": "text/csv", 
        ".json": "application/json",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
    return content_types.get(file_extension.lower(), "application/octet-stream")


def _load_documents_with_filtering(loader: DirectoryLoader, loader_config: Dict[str, Any]) -> List:
    """
    Load documents with custom filtering based on Medium article advanced customizations.
    
    This implements the custom filtering approach suggested in the article:
    - Filter documents based on content length
    - Handle encoding errors gracefully  
    - Preserve important metadata
    - Apply content quality filters
    """
    try:
        documents = loader.load()
        
        # Apply custom filters based on the article's recommendations
        filtered_documents = []
        
        for doc in documents:
            # Filter 1: Skip empty or very short documents (less than 10 characters)
            if len(doc.page_content.strip()) < 10:
                logger.debug(f"Skipping document with insufficient content: {doc.metadata.get('source', 'unknown')}")
                continue
            
            # Filter 2: Skip documents that are too large (more than 1MB of text)
            # This prevents memory issues and focuses on manageable content
            if len(doc.page_content) > 1024 * 1024:  # 1MB
                logger.warning(f"Skipping large document: {doc.metadata.get('source', 'unknown')} ({len(doc.page_content)} chars)")
                continue
            
            # Filter 3: Clean and normalize content
            cleaned_content = doc.page_content.strip()
            if cleaned_content:
                doc.page_content = cleaned_content
                filtered_documents.append(doc)
        
        logger.info(f"Filtered {len(documents)} -> {len(filtered_documents)} documents using {loader_config['name']}")
        return filtered_documents
        
    except Exception as e:
        logger.error(f"Error in document filtering for {loader_config['name']}: {e}")
        # Fallback to basic loading without filtering
        try:
            return loader.load()
        except Exception as fallback_error:
            logger.error(f"Fallback loading also failed for {loader_config['name']}: {fallback_error}")
            return []


async def _ingest_enhanced_documents_to_vector_store(
    user_document_id: int,
    user_id: int, 
    documents: List,
    document_id: str,
    file_info: Dict[str, Any],
    session: Session
):
    """Enhanced background task to ingest batch-processed documents with rich metadata."""
    try:
        # Import here to avoid circular imports
        from app.retrieval.vector_store import get_vector_store
        from app.models.db import UserDocument, IngestionStatus
        
        vector_store = get_vector_store()
        
        # Prepare documents with enhanced metadata for vector store
        texts = []
        metadatas = []
        
        for i, doc in enumerate(documents):
            texts.append(doc.page_content)
            
            # Enhanced metadata with file information and loader details
            # Following Medium article best practices for metadata enrichment
            metadata = {
                # Core identifiers
                "user_id": str(user_id),
                "document_id": document_id,
                "chunk_index": i,
                
                # File information
                "file_name": Path(doc.metadata.get('source', 'unknown')).name,
                "file_type": file_info.get("file_type", "unknown"),
                "loader_type": file_info.get("loader_type", "unknown"),
                "loader_description": file_info.get("loader_description", ""),
                
                # Content metadata
                "source": doc.metadata.get('source'),
                "chunk_type": "enhanced_batch_processed",
                "content_length": len(doc.page_content),
                "total_file_chars": file_info.get("total_chars", 0),
                
                # Processing metadata
                "processing_timestamp": file_info.get("processing_timestamp", datetime.now(timezone.utc).isoformat()),
                "langchain_version": "community",
                "directoryloader_enhanced": True,
                
                # Document-specific metadata (page numbers, etc.)
                "page": str(doc.metadata.get('page')) if doc.metadata.get('page') is not None else None,
                "row": doc.metadata.get('row', None)  # For CSV files
            }
            
            # Add any additional metadata from the document (following article's approach)
            for key, value in doc.metadata.items():
                if key not in metadata and value is not None:
                    # Prefix custom metadata to avoid conflicts
                    metadata[f"doc_{key}"] = str(value)
            
            metadatas.append(metadata)
        
        # Add to vector store with enhanced metadata
        vector_store.add_texts(texts=texts, metadatas=metadatas)
        
        # Update document status with processing details
        user_document = session.get(UserDocument, user_document_id)
        if user_document:
            user_document.status = IngestionStatus.COMPLETED
            user_document.chunk_count = len(documents)
            user_document.total_characters = sum(len(doc.page_content) for doc in documents)
            session.add(user_document)
            session.commit()
        
        logger.info(f"Successfully ingested {len(documents)} enhanced chunks for {file_info['loader_type']} document {document_id}")
        
    except Exception as e:
        logger.error(f"Failed to ingest enhanced batch documents for {document_id}: {e}")
        
        # Update document status to failed
        try:
            user_document = session.get(UserDocument, user_document_id)
            if user_document:
                user_document.status = IngestionStatus.FAILED
                user_document.error_message = str(e)[:500]  # Truncate long errors
                session.add(user_document)
                session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status: {db_error}")



@router.get("/documents", response_model=List[DocumentResponse])
async def list_user_documents(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 50
):
    """Get list of user's uploaded documents."""
    try:
        from sqlmodel import select
        
        # Query user's documents with pagination
        query = (
            select(UserDocument)
            .where(UserDocument.user_id == current_user.id)
            .offset(skip)
            .limit(limit)
            .order_by(UserDocument.created_at.desc())
        )
        
        documents = session.exec(query).all()
        
        return [
            DocumentResponse(
                id=doc.id,
                document_id=doc.document_id,
                filename=doc.filename,
                original_filename=doc.original_filename,
                file_size=doc.file_size,
                content_type=doc.content_type,
                status=doc.status,
                chunk_count=doc.chunk_count,
                total_characters=doc.total_characters,
                error_message=doc.error_message,
                created_at=doc.created_at,
                completed_at=doc.completed_at,
                processing_time_ms=doc.processing_time_ms
            )
            for doc in documents
        ]
        
    except Exception as e:
        logger.error(f"Failed to list documents for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


# @router.post("/batch/folder", response_model=FolderUploadResponse)
@router.post("/batch/upload", response_model=BulkUploadResponse)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_files(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    session_id: str = Form(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Upload multiple documents (PDF, TXT, CSV, JSON, etc.) in one request.
    Accepts multipart/form-data with one or more files and enqueues each for ingestion, scoped to a session.
    """
    try:
        response_items: List[BulkUploadResponseItem] = []

        for file in files:
            # Validate file size and type
            validate_file(file)

            # Save to user-specific directory
            saved_path = save_upload_file(file, current_user.id)

            # Create database record (associate with session)
            document_id = uuid.uuid4().hex
            user_doc = UserDocument(
                user_id=current_user.id,
                session_id=session_id,
                document_id=document_id,
                filename=saved_path.name,
                original_filename=file.filename,
                file_path=str(saved_path),
                file_size=saved_path.stat().st_size,
                content_type=file.content_type or "application/octet-stream",
                status=IngestionStatus.PROCESSING
            )
            session.add(user_doc)
            session.commit()
            session.refresh(user_doc)

            # Enqueue ingestion pipeline
            _, task = ingest_file_for_user(
                user_id=str(current_user.id),
                path=saved_path,
                filename=file.filename,
                document_id=document_id,
                session_id=session_id
            )
            background_tasks.add_task(task)

            response_items.append(
                BulkUploadResponseItem(
                    id=user_doc.id,
                    filename=file.filename,
                    status=user_doc.status,
                    file_size=user_doc.file_size
                )
            )

        # Compute summary
        total_uploaded = len(response_items)
        successful_count = sum(1 for i in response_items if i.status == IngestionStatus.PROCESSING)
        failed_count = total_uploaded - successful_count

        # Return matching the BulkUploadResponse schema
        return BulkUploadResponse(
            documents=response_items,
            total_uploaded=total_uploaded,
            successful_count=successful_count,
            failed_count=failed_count
        )

    except Exception:
        # Log full traceback for debugging
        logger.error("upload_files failed: %s", traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing uploads"
        )


# def _validate_folder_path(folder_path: Path) -> bool:
#     """
#     Validate that the folder path is safe and allowed.
    
#     This function implements security controls to prevent access to unauthorized directories.
#     Updated to allow common user directories like Downloads, Documents, Desktop.
#     """
#     try:
#         # Convert to absolute path for consistent checking
#         abs_path = folder_path.resolve()
#         logger.info(f"Validating folder path: {abs_path}")
        
#         # 1. Check if path is under allowed base directories
#         allowed_base_dirs = [
#             Path(settings.DATA_DIR),  # Your data directory
#             Path.cwd() / "data",      # Project data directory
#             # Common user directories using Path.home()
#             Path.home() / "Downloads",     # User Downloads folder
#             Path.home() / "Documents",     # User Documents folder  
#             Path.home() / "Desktop",       # User Desktop folder
#             # Explicit Windows paths for admin user
#             Path("C:/Users/admin/Downloads"),  # Admin Downloads
#             Path("C:/Users/admin/Documents"),  # Admin Documents
#             Path("C:/Users/admin/Desktop"),    # Admin Desktop
#             # Alternative Windows path format
#             Path("C:\\Users\\admin\\Downloads"),  # Admin Downloads (backslash)
#             Path("C:\\Users\\admin\\Documents"),  # Admin Documents (backslash)
#             Path("C:\\Users\\admin\\Desktop"),    # Admin Desktop (backslash)
#             # Add other allowed directories as needed
#             # Path("/allowed/path/1"),
#             # Path("/allowed/path/2"),
#         ]
        
#         logger.info(f"Checking against {len(allowed_base_dirs)} allowed directories")
        
#         # Check if the path is under any allowed base directory
#         for i, allowed_dir in enumerate(allowed_base_dirs):
#             try:
#                 abs_allowed = allowed_dir.resolve()
#                 logger.debug(f"Checking against allowed dir {i}: {abs_allowed}")
                
#                 # Check if the folder path is under this allowed directory
#                 relative_path = abs_path.relative_to(abs_allowed)
#                 logger.info(f"✅ Folder path {abs_path} is allowed under {abs_allowed} (relative: {relative_path})")
#                 return True  # Path is under an allowed directory
                
#             except ValueError:
#                 # Path is not under this allowed directory, continue checking
#                 logger.debug(f"Path {abs_path} not under {abs_allowed}")
#                 continue
#             except Exception as e:
#                 logger.warning(f"Error checking path {abs_path} against {abs_allowed}: {e}")
#                 continue
        
#         # 2. Deny access to system directories (additional security)
#         forbidden_patterns = [
#             "/etc/", "/var/", "/usr/", "/sys/", "/proc/",  # Linux system dirs
#             "C:\\Windows\\", "C:\\Program Files\\",        # Windows system dirs
#             "C:\\Program Files (x86)\\",                   # Windows x86 programs
#             "/..", "../",                                  # Path traversal attempts
#             "C:/Windows/", "C:/Program Files/",            # Forward slash variants
#             "C:/Program Files (x86)/",
#         ]
        
#         str_path = str(abs_path).replace("\\", "/")  # Normalize for pattern matching
#         for pattern in forbidden_patterns:
#             if pattern.lower() in str_path.lower():
#                 logger.warning(f"Forbidden path pattern detected: {pattern} in {abs_path}")
#                 return False
        
#         # If we reach here, path is not under any allowed directory
#         logger.warning(f"❌ Path not under allowed directories: {abs_path}")
#         logger.info(f"Allowed directories are:")
#         for i, allowed_dir in enumerate(allowed_base_dirs):
#             try:
#                 resolved = allowed_dir.resolve()
#                 logger.info(f"  {i+1}. {resolved}")
#             except Exception as e:
#                 logger.info(f"  {i+1}. {allowed_dir} (error resolving: {e})")
        
#         return False
        
#     except Exception as e:
#         logger.error(f"Error validating folder path {folder_path}: {e}")
#         return False


async def _process_folder_with_directoryloader(
    folder_path: Path,
    folder_request: FolderUploadRequest,
    current_user: User,
    session: Session,
    background_tasks: BackgroundTasks
) -> List[BulkUploadResponseItem]:
    """Process folder using DirectoryLoader for each file type."""
    
    # Use all supported file types (simplified - no filtering)
    supported_extensions = {'.pdf', '.txt', '.csv', '.json', '.docx'}
    
    # Enhanced DirectoryLoader with multiple file type support
    file_type_loaders = _get_file_type_loaders()
    all_documents = []
    processed_files = {}
    processing_errors = []
    
    logger.info(f"Processing folder {folder_path} using enhanced DirectoryLoader")
    
    # Process each file type with specific loaders
    for file_pattern, loader_config in file_type_loaders.items():
        # Skip file types not in supported extensions
        pattern_ext = file_pattern.split('*')[-1]  # Extract extension from pattern
        if pattern_ext not in supported_extensions:
            continue
            
        try:
            # Always use recursive pattern (simplified)
            # file_pattern already contains "**/" for recursive processing
            
            # Create DirectoryLoader for this file type
            loader = DirectoryLoader(
                str(folder_path),
                glob=file_pattern,
                loader_cls=loader_config["loader_class"],
                loader_kwargs=loader_config.get("kwargs", {}),
                show_progress=True,
                use_multithreading=True,
                max_concurrency=4,
                silent_errors=False,
                recursive=True  # Always recursive
            )
            
            # Load documents with custom filtering
            documents = _load_documents_with_filtering(loader, loader_config)
            
            if documents:
                logger.info(f"Loaded {len(documents)} documents from {file_pattern} files using {loader_config['name']}")
                all_documents.extend(documents)
                
                # Track processed files by type
                for doc in documents:
                    source_file = doc.metadata.get('source', 'unknown')
                    filename = Path(source_file).name
                    file_ext = Path(filename).suffix.lower()
                    
                    if filename not in processed_files:
                        processed_files[filename] = {
                            "chunks": [],
                            "file_type": file_ext,
                            "loader_type": loader_config["name"],
                            "loader_description": loader_config.get("description", ""),
                            "total_chars": 0,
                            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
                            "source_path": source_file
                        }
                    
                    processed_files[filename]["chunks"].append(doc)
                    processed_files[filename]["total_chars"] += len(doc.page_content)
                    
        except Exception as e:
            error_msg = f"Failed to process {file_pattern} files with {loader_config['name']}: {str(e)}"
            logger.warning(error_msg)
            processing_errors.append({
                "file_pattern": file_pattern,
                "loader_name": loader_config["name"],
                "error": str(e)
            })
            continue
    
    # Process each file and create database records
    response_items: List[BulkUploadResponseItem] = []
    
    for filename, file_info in processed_files.items():
        try:
            # Create database record for the file
            document_id = uuid.uuid4().hex
            source_path = Path(file_info["source_path"])
            file_size = source_path.stat().st_size if source_path.exists() else 0
            
            # Determine content type based on file extension
            content_type = _get_content_type(file_info["file_type"])
            
            user_document = UserDocument(
                user_id=current_user.id,
                document_id=document_id,
                filename=filename,
                original_filename=filename,
                file_path=str(source_path),  # Store original path
                file_size=file_size,
                content_type=content_type,
                status=IngestionStatus.PROCESSING
            )
            
            session.add(user_document)
            session.commit()
            session.refresh(user_document)
            
            # Queue background task for vector store ingestion
            background_tasks.add_task(
                _ingest_enhanced_documents_to_vector_store,
                user_document.id,
                current_user.id,
                file_info["chunks"],
                document_id,
                file_info,
                session
            )
            
            response_items.append(BulkUploadResponseItem(
                id=user_document.id,
                filename=filename,
                status=IngestionStatus.PROCESSING,
                file_size=file_size
            ))
            
            logger.info(f"Queued {len(file_info['chunks'])} chunks from {filename} ({file_info['loader_type']}) for processing")
            
        except Exception as e:
            logger.error(f"Failed to process file {filename}: {e}")
            response_items.append(BulkUploadResponseItem(
                id=-1,
                filename=filename,
                status="failed",
                error_message=str(e)
            ))
    
    return response_items
