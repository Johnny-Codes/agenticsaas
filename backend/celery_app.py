import os
import time
import random
from celery import Celery
from celery.signals import task_postrun
from celery.utils.log import get_task_logger

from config import settings

logger = get_task_logger(__name__)

# Initialize Celery app
celery = Celery(
    "fastapi_celery_app",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

celery.autodiscover_tasks(["backend.tasks"])


# @celery.task
# def test_task(a, b):
#     return f"Test task received: {a}, {b}"
