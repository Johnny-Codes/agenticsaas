from fastapi import APIRouter
from celery.result import AsyncResult
from celery_app import (
    celery,
)  # Adjust this import to your Celery app instance

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)


@router.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    try:
        task_result = AsyncResult(task_id, app=celery)
    except Exception as e:  # More generic catch if celery_app itself is problematic
        return {
            "error": f"Celery app not configured or available for status check: {str(e)}"
        }

    if task_result.ready():
        if task_result.successful():
            return {
                "task_id": task_id,
                "status": task_result.status,
                "result": task_result.result,
            }
        else:
            return {
                "task_id": task_id,
                "status": task_result.status,
                "error": str(task_result.info),  # Contains exception if task failed
            }
    else:
        return {"task_id": task_id, "status": task_result.status}


@router.get("/active_tasks")
async def get_active_tasks():
    try:
        inspector = celery.control.inspect()
        active_tasks_data = inspector.active()

        if not active_tasks_data:
            return {"message": "No active workers found or no tasks currently active."}

        # The structure of active_tasks_data is usually:
        # {'worker_name@host': [{'id': 'task_id', 'name': 'task_name', ...}, ...]}
        # You might want to flatten or reformat this for easier consumption
        all_active_tasks = []
        for worker_name, tasks in active_tasks_data.items():
            if tasks:  # Ensure there are tasks for this worker
                for task_info in tasks:
                    task_info["worker"] = worker_name  # Add worker name to task info
                    all_active_tasks.append(task_info)

        if not all_active_tasks:
            return {"message": "No tasks currently active across all workers."}

        return {"active_tasks": all_active_tasks}
    except Exception as e:
        # This can happen if the broker is down or workers are not reachable
        return {"error": f"Could not inspect active tasks: {str(e)}"}
