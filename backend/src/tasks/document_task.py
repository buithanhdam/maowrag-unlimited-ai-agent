# src/tasks/document_task.py
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, List, Dict, Union
import uuid
from datetime import datetime
import celery
from pydantic import BaseModel, Field
from src.celery_worker import celery_app
from src.db.aws import get_aws_s3_client
from src.readers import FileExtractor, parse_multiple_files
from src.config import global_config
from src.logger import get_formatted_logger
import tiktoken
import traceback

logger = get_formatted_logger(__file__)

# Initialize services that will be used by tasks
file_extractor = FileExtractor()
s3_client = get_aws_s3_client()


class TaskBase(BaseModel):
    """Base model for celery tasks"""

    status: str = Field(
        default="pending", description="Task status (success, error, pending)"
    )
    task_id: Optional[str] = Field(default=None, description="Celery task ID")
    task_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional task information"
    )
    message: Optional[str] = Field(default=None, description="Task message")


class TaskResponse(TaskBase):
    """Response model for celery tasks"""

    pass


def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
    except Exception as e:
        logger.warning(f"Error counting tokens: {str(e)}. Using fallback method.")
        # Fallback: rough estimate of 4 characters per token
        return len(string) // 4


@celery_app.task(name="document.upload", bind=True, max_retries=3)
def upload_document(
    self: celery.Task, bucket_name: str, file_content: bytes, filename: str
) -> Dict[str, Any]:
    """
    Upload a document to storage

    Args:
        bucket_name: S3 bucket name or storage location identifier
        file_content: Binary content of the file
        filename: Original filename

    Returns:
        TaskResponse object with upload results
    """
    temp_file = None
    try:
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100})

        # Create temp directory if it doesn't exist
        temp_dir = Path(tempfile.gettempdir()) / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)

        original_filename = Path(filename)
        # Ensure extension has a leading dot
        extension = (
            original_filename.suffix.lower() if original_filename.suffix else ".unknown"
        )

        # Create temp file with unique name
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=extension, dir=temp_dir
        )

        # Write content to temp file
        with open(temp_file.name, "wb") as f:
            f.write(file_content)

        self.update_state(state="PROGRESS", meta={"current": 50, "total": 100})

        # Generate storage path
        date_path = datetime.now().strftime("%Y/%m/%d")
        file_name = f"{uuid.uuid4()}_{filename}"

        # Upload to S3 - Commented out for now
        file_path_in_s3 = s3_client.upload_file(
            bucket_name=bucket_name,
            object_name=os.path.join(date_path, file_name),
            file_path=str(temp_file.name),
        )

        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100})

        return TaskResponse(
            status="success",
            task_id=self.request.id,
            task_info={
                "task_id": self.request.id,
                "task_name": self.request.task,
                "task_retry": self.request.retries,
                "bucket_name": bucket_name,
                "file_source": file_path_in_s3,
                "file_name": filename,
            },
            message="Document uploaded successfully",
        ).model_dump()

    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        logger.error(traceback.format_exc())

        try:
            self.retry(countdown=10 * (self.request.retries + 1), exc=e)
        except self.MaxRetriesExceededError:
            return TaskResponse(
                status="error",
                task_id=self.request.id,
                task_info={
                    "task_id": self.request.id,
                    "task_name": self.request.task,
                    "task_retry": self.request.retries,
                    "bucket_name": bucket_name,
                    "file_source": "",
                    "file_name": filename,
                    "error": str(e),
                },
                message=f"Retry limit exceeded: {str(e)}",
            ).model_dump()
    finally:
        # Cleanup temp file
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {str(e)}")


@celery_app.task(name="document.parse", bind=True, max_retries=3)
def parse_document(self: celery.Task, file_path: str) -> Dict[str, Any]:
    """
    Parse a document and extract its content

    Args:
        file_path: Path to the document file

    Returns:
        TaskResponse with extracted documents and token count
    """
    try:
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100})

        # Verify file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Process the document using FileExtractor
        extractor = file_extractor.get_extractor_for_file(file_path)
        if not extractor:
            raise ValueError(f"No suitable extractor found for file: {file_path}")

        self.update_state(state="PROGRESS", meta={"current": 30, "total": 100})

        # Parse the files
        documents = parse_multiple_files(file_path, extractor)
        if not documents:
            logger.warning(f"No content extracted from file: {file_path}")

        self.update_state(state="PROGRESS", meta={"current": 70, "total": 100})

        # Count tokens for all documents
        total_tokens = 0
        serializable_documents = []

        for doc in documents:
            doc_tokens = num_tokens_from_string(doc.text)
            total_tokens += doc_tokens

            # Convert Document objects to serializable dictionaries
            serializable_documents.append(
                {
                    "id": str(uuid.uuid4()),
                    "text": doc.text,
                    "metadata": doc.metadata,
                    "token_count": doc_tokens,
                }
            )

        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100})

        return TaskResponse(
            status="success",
            task_id=self.request.id,
            task_info={
                "task_id": self.request.id,
                "task_name": self.request.task,
                "task_retry": self.request.retries,
                "file_path": file_path,
                "documents": serializable_documents,
                "total_tokens": total_tokens,
                "document_count": len(documents),
            },
            message="Document processed successfully",
        ).model_dump()
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        logger.error(traceback.format_exc())

        try:
            self.retry(countdown=10 * (self.request.retries + 1), exc=e)
        except self.MaxRetriesExceededError:
            return TaskResponse(
                status="error",
                task_id=self.request.id,
                task_info={
                    "task_id": self.request.id,
                    "task_name": self.request.task,
                    "task_retry": self.request.retries,
                    "file_path": file_path,
                    "documents": [],
                    "total_tokens": 0,
                    "error": str(e),
                },
                message=f"Retry limit exceeded: {str(e)}",
            ).model_dump()

def create_error_response(
    task: celery.Task,
    file_path: str,
    message: str,
    document_status: str = None,
    error: str = None,
) -> Dict[str, Any]:
    """Create a standardized error response"""
    response = {
        "task_id": task.request.id,
        "task_name": task.request.task,
        "task_retry": task.request.retries,
        "file_path": file_path,
    }

    if document_status:
        response["document_status"] = document_status

    if error:
        response["error"] = error

    return TaskResponse(
        status="error", task_id=task.request.id, task_info=response, message=message
    ).model_dump()