from celery_app import celery


@celery.task
def test_task(a, b):
    def delay():
        pass

    return f"Test task received: {a}, {b}"
