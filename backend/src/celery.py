import os
from celery import Celery
from dotenv import load_dotenv
from src.config import global_config
from src.logger import get_formatted_logger

logger = get_formatted_logger(__file__)
load_dotenv()

celery_app = Celery(
    "document_task",
    backend=global_config.CELERY_BROKER_URL,
    broker=global_config.CELERY_BROKER_URL,
    include=["src.tasks.document_task"],
    log=logger,
    
)

celery_app.conf.update(
    result_backend=global_config.CELERY_BROKER_URL,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)