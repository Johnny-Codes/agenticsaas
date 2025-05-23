import os
from fastapi import APIRouter
from celery_app import celery

from tasks.tests import test_task

router = APIRouter(
    prefix="/testing",
    tags=["Testing"],
)

testing_agent_prompt = (
    "You are a requirements engineer expert. Extract all requirements from the document and return a list of strings. Do not include any additional text or explanation but you can reformat the text to make it readable.",
)


@router.post("/test/")
def test():
    # Example arguments for your test_task
    arg1 = "hello"
    arg2 = "world"

    # Call the Celery task asynchronously
    result = test_task.delay(arg1, arg2)

    # Optionally, wait for the result (not recommended for production)
    output = result.get(timeout=10)
    return {"task_id": result.id, "result": output}
