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


@celery.task(bind=True)
def process_file_task(self, filename: str):
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    total_words = 0

    try:
        logger.info(f"Processing file: {filename}")
        # Update task state (optional, for finer-grained tracking than PENDING/SUCCESS/FAILURE)
        self.update_state(
            state="STARTED", meta={"message": f"Starting to process {filename}..."}
        )

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            total_lines = len(lines)

            for i, line in enumerate(lines):
                # Simulate some processing time
                time.sleep(random.uniform(0.05, 0.2))  # Longer sleep for demonstration

                words_in_line = len(line.strip().split())
                total_words += words_in_line

                progress_percentage = (i + 1) / total_lines * 100
                logger.info(
                    f"Task {self.request.id}: Processed line {i+1}/{total_lines}, words: {words_in_line}"
                )

                # Update task progress in Celery's result backend
                # Frontend will poll this info via the /task-status endpoint
                if (i + 1) % 5 == 0 or (
                    i + 1
                ) == total_lines:  # Update every 5 lines or at end
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "progress": f"{progress_percentage:.1f}%",
                            "message": f"Processed {total_words} words so far from {filename}...",
                            "words_counted": total_words,
                        },
                    )

        result_message = f"File '{filename}' processed. Total words: {total_words}"
        logger.info(f"Task {self.request.id}: {result_message}")

        return {"filename": filename, "total_words": total_words, "status": "SUCCESS"}

    except FileNotFoundError:
        error_msg = f"File not found: {file_path}"
        logger.error(error_msg)
        self.update_state(state="FAILURE", meta={"message": error_msg})
        raise
    except Exception as e:
        error_msg = f"Error processing file {filename}: {e}"
        logger.error(error_msg)
        self.update_state(state="FAILURE", meta={"message": error_msg})
        raise


# Optional: Cleanup uploaded file after task completion
@task_postrun.connect
def remove_uploaded_file(
    sender=None,
    task_id=None,
    task=None,
    args=None,
    kwargs=None,
    retval=None,
    state=None,
    **other,
):
    if state in ["SUCCESS", "FAILURE"]:
        if args and len(args) > 0:
            filename = args[0]
            file_path = os.path.join(settings.UPLOAD_DIR, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up uploaded file: {file_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove file {file_path}: {e}")
