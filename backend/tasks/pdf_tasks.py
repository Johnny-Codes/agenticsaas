from celery_app import celery
from helper_functions.parse import parse_pdf


# @celery.task(name="tasks.pdf_tasks.get_pdf_data_task")
# @celery.task
# def get_pdf_data_task(file_path):
#     # Convert the async parse_pdf to a sync function for Celery
#     import asyncio

#     # Run the async parse_pdf in a new event loop
#     result = asyncio.run(parse_pdf(file_path))
#     return result


@celery.task
def get_pdf_data_task(file_path):
    return parse_pdf(file_path)
