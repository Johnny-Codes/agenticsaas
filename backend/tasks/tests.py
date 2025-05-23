from backend.celery_app import celery


@celery.task
def test_task(a, b):
    return f"Test task received: {a}, {b}"
