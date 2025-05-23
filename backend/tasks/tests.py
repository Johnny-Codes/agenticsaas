"""
Need to figure out how to be able to break the celery tasks from celery_app.py
"""

from celery_app import celery


@celery.task
def test_task(a, b):
    return f"bitch butt Test task received: {a}, {b}"
