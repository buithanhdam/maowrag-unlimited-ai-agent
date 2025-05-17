# src/tasks/document_task.py
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
import uuid
from datetime import datetime
import celery
from sqlalchemy import select
from sqlalchemy.orm import Session
import traceback

from src.celery_worker import celery_app
from src.readers import FileExtractor, parse_multiple_files
from src.config import global_config
from src.logger import get_formatted_logger
from src.db import Document, get_local_session, Task,KnowledgeBase,RAGConfig,get_aws_s3_client,DocumentChunk
from .design import count_tokens_from_string, clean_text_for_db
from src.enums import DocumentStatusType, TaskStatusType,LLMProviderType
from src.rag import RAGManager, BaseRAG

logger = get_formatted_logger(__file__)
def get_rag_from_kb(session: Session, kb_id: int) -> BaseRAG:
        kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            logger.error(f"KnowledgeBase with ID {kb_id} not found")
            return None
        # Get RAG config
        rag_config: RAGConfig = kb.rag_config
        if not rag_config:
            logger.error(f"RAGConfig not found for KnowledgeBase ID {kb_id}")
            return None
        # Initialize RAG manager
        rag_manager = RAGManager.create_rag(
            rag_type=rag_config.rag_type,
            vector_db_url=global_config.QDRANT_URL,
            llm_type=LLMProviderType.GOOGLE,
            chunk_size=rag_config.chunk_size,
            chunk_overlap=rag_config.chunk_overlap,
        )
        return rag_manager
@celery_app.task(name="document.upload", bind=True, max_retries=3)
def upload_document(
    self: celery.Task,
    bucket_name: str,
    file_content: bytes,
    filename: str,
    session: Session = None,
) -> Dict[str, Any]:
    """
    Upload a document to storage

    Args:
        bucket_name: S3 bucket name or storage location identifier
        file_content: Binary content of the file
        filename: Original filename
        session: Database session (optional)

    Returns:
        TaskResponse object with upload results
    """
    # Use provided session or create a new one
    db_session = session or get_local_session()
    s3_client = get_aws_s3_client()
    temp_file = None
    temp_file_path = None
    
    try:
        # Fetch job and related document in a single operation
        result = db_session.query(Document, Task).join(
            Task, Document.task_id == Task.id
        ).filter(Task.id == self.request.id).first()
        document, task = result
        if not document or not task:
            raise ValueError(f"Document with TaskID {self.request.id} not found")
        
        # Update state and job status
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100})
        document.status = DocumentStatusType.UPLOADING
        db_session.add(document)
        db_session.flush()
        
        # Generate storage path
        original_filename = Path(filename)
        extension = original_filename.suffix.lower() if original_filename.suffix else ".unknown"
        date_path = datetime.now().strftime("%Y/%m/%d")
        file_name = f"{uuid.uuid4()}_{filename}"
        
        # Create temp directory
        temp_dir = Path(tempfile.gettempdir()) / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Use context manager for temp file handling
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension, dir=temp_dir) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            self.update_state(state="PROGRESS", meta={"current": 50, "total": 100})
            
            # Set up storage path
            file_path = os.path.join(date_path, file_name)
            
            file_path_in_s3 = s3_client.upload_file(
                bucket_name=bucket_name,
                object_name=file_path,
                file_path=temp_file_path,
            )
            document.source = file_path_in_s3
            document.status = DocumentStatusType.UPLOADED
            
            # Update state and create response
            self.update_state(state="PROGRESS", meta={"current": 100, "total": 100})
            
            # Update task attributes directly
            task.status = TaskStatusType.COMPLETED
            task.name = self.request.task
            task.retry = self.request.retries
            task.extra_info = {
                "document_uuid": document.uuid,
                "bucket_name": bucket_name,
                "file_source": file_path_in_s3,
                "file_name": filename,
            }
            task.message = "Document uploaded successfully"
            
            # Save changes
            db_session.add(document)
            db_session.add(task)
            
            # Return task information as dictionary
            return {
                "status": task.status.value,
                "name": task.name,
                "retry": task.retry,
                "extra_info": task.extra_info,
                "message": task.message
            }
            
        finally:
            # Clean up temp file - moved to finally block for better handling
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        logger.error(traceback.format_exc())
        
        try:
            # Try to retry the task
            logger.info(f"Retrying task {self.request.id}, attempt {self.request.retries + 1}")
            self.retry(countdown=10 * (self.request.retries + 1), exc=e)
        except self.MaxRetriesExceededError:
            # Handle max retries case
            if 'document' in locals() and document and 'task' in locals() and task:
                document.status = DocumentStatusType.FAILED
                task.status = TaskStatusType.FAILED
                task.name = self.request.task
                task.retry = self.request.retries
                task.extra_info = {
                    "document_uuid": document.uuid,
                    "bucket_name": bucket_name,
                    "file_source": "",
                    "file_name": filename,
                }
                task.message = f"Task failed after {self.request.retries} retries: {str(e)}"
                
                db_session.add(task)
                db_session.add(document)
                
                # Return task information as dictionary
                return {
                    "status": task.status.value,
                    "name": task.name,
                    "retry": task.retry,
                    "extra_info": task.extra_info,
                    "message": task.message
                }
            else:
                # In case the document and task were not found
                return {
                    "status": TaskStatusType.FAILED.value,
                    "name": self.request.task,
                    "retry": self.request.retries,
                    "extra_info": {},
                    "message": f"Task failed: {str(e)}"
                }
    
    finally:
        # Only commit if we created the session
        if session is None and db_session:
            try:
                db_session.commit()
            except Exception as commit_error:
                logger.error(f"Error committing transaction: {str(commit_error)}")
                db_session.rollback()
                
                # Re-raise if this wasn't already an error case
                if 'e' not in locals():
                    raise
            finally:
                db_session.close()
                
@celery_app.task(name="document.parse", bind=True, max_retries=3)
def parse_document(
    self: celery.Task,
    kb_uuid: str,
    session: Session = None,
) -> Dict[str, Any]:
    """
    Parse a document and extract its content

    Args:
        kb_uuid: kb_uuid
        session: Database session (optional)

    Returns:
        TaskResponse with extracted documents and token count
    """
    # Use provided session or create a new one
    file_extractor = FileExtractor()
    db_session = session or get_local_session()
    s3_client = get_aws_s3_client()
    temp_file = None
    document_source = None  # Store document source path for error handling
    
    try:
        # Fetch job and related document in a single operation
        result = db_session.query(Document, Task).join(
            Task, Document.task_id == Task.id
        ).filter(Task.id == self.request.id).first()
        
        if not result:
            raise ValueError(f"Document with TaskID {self.request.id} not found")
            
        document, task = result
        document_source = document.source  # Store for error handling
        
        # Update state and task status
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100})
        task.status = TaskStatusType.PROCESSING
        task.message = "Processing document"
        db_session.add(task)
        db_session.flush()

        # Create temp directory
        temp_dir = Path(tempfile.gettempdir()) / "downloads"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Create temp file
        extension = Path(document.source).suffix
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=extension, dir=temp_dir
        )

        # Update status to processing
        document.status = DocumentStatusType.PROCESSING
        db_session.flush()

        try:
            # Download file from S3
            try:
                s3_client.download_file(
                    file_url=document.source, file_path_to_save=temp_file.name
                )
            except Exception as e:
                logger.error(f"S3 download failed: {str(e)}")
                error_info = {
                    "document_uuid": document.uuid,
                    "file_path": document.source,
                    "documents": [],
                    "total_tokens": 0,
                    "document_count": 0,
                }
                
                document.status = DocumentStatusType.FAILED
                task.status = TaskStatusType.FAILED
                task.message = f"Error processing document: {document.source}, Failed to download file from S3"
                task.extra_info = error_info
                
                db_session.add(task)
                db_session.add(document)
                return {
                    "status": "error",
                    "id": self.request.id,
                    "name": self.request.task,
                    "retry": self.request.retries,
                    "extra_info": error_info,
                    "message": task.message,
                }

            self.update_state(state="PROGRESS", meta={"current": 30, "total": 100})

            task.message = "Extracting content from document"
            db_session.add(task)
            db_session.flush()
            rag = get_rag_from_kb(db_session, document.kb_id)
            if not rag:
                error_info = {
                    "document_uuid": document.uuid,
                    "file_path": document.source,
                    "documents": [],
                    "total_tokens": 0,
                    "document_count": 0,
                }
                
                document.status = DocumentStatusType.FAILED
                task.status = TaskStatusType.FAILED
                task.message = f"Error processing document: {document.source}, rag config for kb {document.kb_id} not found"
                task.extra_info = error_info
                
                db_session.add(task)
                db_session.add(document)
                return {
                    "status": "error",
                    "id": self.request.id,
                    "name": self.request.task,
                    "retry": self.request.retries,
                    "extra_info": error_info,
                    "message": task.message,
                }
                
            # Get appropriate extractor for the file type
            extractor = file_extractor.get_extractor_for_file(temp_file.name)
            if not extractor:
                error_info = {
                    "document_uuid": document.uuid,
                    "file_path": document.source,
                    "documents": [],
                    "total_tokens": 0,
                    "document_count": 0,
                }
                
                document.status = DocumentStatusType.FAILED
                task.status = TaskStatusType.FAILED
                task.message = f"Error processing document: {document.source}, extractor not found for {temp_file.name}"
                task.extra_info = error_info
                
                db_session.add(task)
                db_session.add(document)
                return {
                    "status": "error",
                    "id": self.request.id,
                    "name": self.request.task,
                    "retry": self.request.retries,
                    "extra_info": error_info,
                    "message": task.message,
                }
                
            # Parse the files
            parsed_documents = parse_multiple_files(temp_file.name, extractor)
            if not parsed_documents:
                logger.warning(f"No content extracted from file: {document.source}")
                error_info = {
                    "document_uuid": document.uuid,
                    "file_path": document.source,
                    "documents": [],
                    "total_tokens": 0,
                    "document_count": 0,
                }
                
                document.status = DocumentStatusType.FAILED
                task.status = TaskStatusType.FAILED
                task.message = f"Error processing document: {document.source}, failed to parse content {temp_file.name}: {extractor}"
                task.extra_info = error_info
                
                db_session.add(task)
                db_session.add(document)
                return {
                    "status": "error",
                    "id": self.request.id,
                    "name": self.request.task,
                    "retry": self.request.retries,
                    "extra_info": error_info,
                    "message": task.message,
                }

            self.update_state(state="PROGRESS", meta={"current": 70, "total": 100})

            task.message = "Parse content from list of chunk document"
            db_session.add(task)
            db_session.flush()
            
            # Count tokens for all documents
            total_tokens = 0
            serializable_documents = []
            for parsed_document in parsed_documents:
                chunks = rag.process_document(
                    document=parsed_document,
                    document_id=document.id,
                    collection_name=kb_uuid,
                    metadata={
                        **parsed_document.metadata,
                        "file_path": document.name,
                        "created_at": document.created_at.isoformat(),
                    },
                )
                # Create chunks in database
                for chunk_idx, chunk_data in enumerate(chunks):
                    chunk_tokens=count_tokens_from_string(chunk_data.text)
                    clean_text = clean_text_for_db(chunk_data.text)
                    chunk_uuid = chunk_data.metadata.get("chunk_id", str(uuid.uuid4()))
                    chunk = DocumentChunk(
                        document_id=document.id,
                        uuid = chunk_uuid,
                        content=clean_text,
                        chunk_index=chunk_idx,
                        dense_embedding=chunk_data.metadata["dense_embedding"],
                        sparse_embedding=chunk_data.metadata["sparse_embedding"],
                        extra_info=chunk_data.metadata,
                        tokens = chunk_tokens
                    )
                    db_session.add(chunk)
                    total_tokens += chunk_tokens
                    # Convert Document objects to serializable dictionaries
                    serializable_documents.append(
                        {
                            "id": chunk_uuid,
                            "text": clean_text,
                            "metadata": chunk_data.metadata,
                            "token_count": chunk_tokens,
                        }
                    )
                    

            # Update document status
            document.status = DocumentStatusType.PROCESSED
            document.tokens = total_tokens
            db_session.add(document)
            
            # Update task status and info
            task.status = TaskStatusType.COMPLETED
            task.message = "Document parsed successfully"
            task.extra_info = {
                "document_uuid": document.uuid,
                "file_path": document.source,
                "documents": serializable_documents,
                "total_tokens": total_tokens,
                "document_count": len(serializable_documents),
            }
            db_session.add(task)
            
            self.update_state(state="PROGRESS", meta={"current": 100, "total": 100})
            
            # Only commit if we created the session
            if session is None:
                db_session.commit()
                
            return {
                "status": "success",
                "id": self.request.id,
                "name": self.request.task,
                "retry": self.request.retries,
                "extra_info": task.extra_info,
                "message": "Document parsed successfully",
            }
                
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {str(e)}")
        
    except Exception as e:
        # Special handling for missing files
        logger.error(f"Error processing document: {document_source or 'unknown'}")
        logger.error(traceback.format_exc())
        try:
            # Try to retry the task
            logger.info(f"Retrying task {self.request.id}, attempt {self.request.retries + 1}")
            self.retry(countdown=10 * (self.request.retries + 1), exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for task {self.request.id}")
            if 'document' in locals() and document and 'task' in locals() and task:
                error_info = {
                    "document_uuid": document.uuid,
                    "file_path": document.source,
                    "documents": [],
                    "total_tokens": 0,
                    "document_count": 0,
                }
                
                document.status = DocumentStatusType.FAILED
                task.status = TaskStatusType.FAILED
                task.message = f"Error processing document: {document.source}, with max retries {self.request.retries}"
                task.extra_info = error_info
                
                db_session.add(task)
                db_session.add(document)
                
                if session is None:
                    db_session.commit()
                
                return {
                    "status": "error",
                    "id": self.request.id,
                    "name": self.request.task,
                    "retry": self.request.retries,
                    "extra_info": error_info,
                    "message": f"Error processing document: {document.source}, with max retries {self.request.retries}",
                }
            else:
                # In case document and task were not found
                return {
                    "status": "error",
                    "id": self.request.id,
                    "name": self.request.task,
                    "retry": self.request.retries,
                    "extra_info": {
                        "file_path": document_source or "unknown",
                    },
                    "message": f"Error processing document: {str(e)}",
                }
    finally:
        # Only close if we created the session
        if session is None and 'db_session' in locals() and db_session:
            db_session.close()