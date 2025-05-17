from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict, Union
import tiktoken
import re

class TaskBase(BaseModel):
    """Base model for celery tasks"""
    status: str = Field(
        default="pending", description="Task status (success, error, pending)"
    )
    task_id: Optional[str] = Field(default=None, description="Celery task ID")
    task_name: Optional[str] = Field(default=None, description="Task name")
    task_retry: Optional[int] = Field(default=0, description="Task retry count")
    task_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional task information"
    )
    message: Optional[str] = Field(default=None, description="Task message")


class TaskResponse(TaskBase):
    """Response model for celery tasks"""
    pass

def count_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
    except Exception as e:
        # Fallback: rough estimate of 4 characters per token
        return len(string)

def clean_text_for_db(text: str) -> str:
    """
    Clean text to ensure it's safe for database insertion.
    Removes null bytes and all non-printable/control characters.
    """
    if not isinstance(text, str):
        return text  # skip non-str types

    # Remove null bytes and other control characters (ASCII 0–31, 127)
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)

    # Optionally: Remove non-characters in Unicode (U+FDD0–U+FDEF and others)
    text = re.sub(r'[\uFDD0-\uFDEF]', '', text)
    text = re.sub(r'[\uFFFE\uFFFF]', '', text)  # non-characters

    # Remove invisible formatting characters (optional, common in copy-paste)
    text = re.sub(r'[\u200B-\u200F\u202A-\u202E\u2060-\u206F]', '', text)

    return text.strip()