# src/celery.py
from celery import Celery
from src.config import global_config

celery_app = Celery(
    "document_task",
    backend=global_config.CELERY_BROKER_URL,
    broker=global_config.CELERY_BROKER_URL,
    include=["src.tasks.document_task"],
)

celery_app.conf.update(
    result_backend=global_config.CELERY_BROKER_URL,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=300,  # 5 minutes
    worker_max_tasks_per_child=200,  # Restart worker after 200 tasks
    worker_prefetch_multiplier=4,  # One task at a time
)