import os
import pathlib
from typing import Union, List

from fastapi import FastAPI, File, UploadFile

import pymupdf4llm

from pydantic import BaseModel

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent

# from ollama import Client as OllamaClient


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/pdf_upload/")
async def upload_pdf_file(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        return {"error": "Only PDF files are allowed."}

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    parsed_true = await parse_pdf(file_path)

    return {
        "message": f"PDF file {file.filename} uploaded successfully to {file_path} and {parsed_true}."
    }


class PDFData(BaseModel):
    title: str
    authors: List[str]


provider = OpenAIProvider(base_url="http://host.docker.internal:11434/v1")
# ollama_model = OpenAIModel(model_name="llama3.2:latest", provider=provider)
ollama_model = OpenAIModel(model_name="llama3.2", provider=provider)

pdf_title_agent = Agent(
    ollama_model,
    system_prompt=(
        "You are a helpful assistant. Extract the information asked for. "
        "Fix any formatting issues in the title (e.g., remove extra spaces, convert to title case, etc.). "
        "Your response must be a JSON object with the following format: {'': '<>'}. "
        "Do not include any additional text or explanation."
    ),
    output_type=PDFData,
)


async def parse_pdf(file_path: str):
    md_text = pymupdf4llm.to_markdown(file_path)
    md_file_path = f"{file_path[:-4]}.md"
    pathlib.Path(md_file_path).write_bytes(md_text.encode())
    pdf_data = await get_pdf_title(md_text)

    return f"{pdf_data}"


async def get_pdf_title(md_text: str):
    try:
        data = await pdf_title_agent.run(
            f"What is the title of the following document and who are the authors? {md_text[:500]}",
        )
        print(f"Model response: {data}")
        return data
    except Exception as e:
        print(f"Error: {e}")
        raise


# this looks cool https://docling-project.github.io/docling/examples/export_figures/
