import os
import uuid
from fastapi import APIRouter, UploadFile, File

from tasks.pdf_tasks import get_pdf_data_task

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads/")
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(
    prefix="/requirements",
    tags=["Requirements"],
)


@router.get("/")
async def test_req():
    return "OK"


@router.post("/pdf_upload")
async def upload_req(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        return {"error": "Only PDF files are allowed."}
    file_name = f"{uuid.uuid4().hex}.pdf"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    x = get_pdf_data_task.delay(file_path)

    return {
        "message": f"PDF file {file.filename} uploaded successfully to {file_path} x: {x.id}."
    }
