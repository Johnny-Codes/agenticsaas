from ..tasks import celery


@celery.task
def test_task():
    return "42"
