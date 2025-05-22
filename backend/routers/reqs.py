import os
from fastapi import APIRouter, UploadFile, File

from helper_functions.parse import parse_pdf

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

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    parsed_true = await parse_pdf(file_path)

    return {
        "message": f"PDF file {file.filename} uploaded successfully to {file_path} and {parsed_true}."
    }
