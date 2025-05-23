from celery_app import celery


@celery.task
def test_task(a, b):
    return f"bitch butt Test task received: {a}, {b}"
