import os
import pathlib
from typing import Union, List
import json  # Added for parsing the JSON response from OpenAI
import re  # Add this import at the top of your file

from fastapi import FastAPI, File, UploadFile, HTTPException

import pymupdf4llm
import pymupdf
from multi_column import column_boxes

from pydantic import BaseModel

# pydantic-ai imports are still here for other agents if needed
# from pydantic_ai.models.openai import OpenAIModel
# from pydantic_ai.providers.openai import OpenAIProvider
# from pydantic_ai import Agent

# Import the OpenAI library
from openai import AsyncOpenAI

from chonkie import RecursiveChunker
from agno.agent import Agent
from agno.document.chunking.agentic import AgenticChunking
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.pgvector import PgVector

app = FastAPI()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads/")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/agentic_chunking/")
async def agentic_chunking():

    # Get vector DB URL from environment (set in docker-compose)
    vector_db_url = os.getenv("VECTOR_DATABASE_URL")
    if not vector_db_url:
        raise HTTPException(
            status_code=500, detail="VECTOR_DATABASE_URL not set in environment."
        )

    # PgVector expects SQLAlchemy-style URL, often 'postgresql+psycopg2://...'
    if vector_db_url.startswith("postgresql://"):
        vector_db_url = vector_db_url.replace(
            "postgresql://", "postgresql+psycopg2://", 1
        )

    table_name = "singh2018_agentic_chunking"

    knowledge_base = PDFUrlKnowledgeBase(
        urls=[
            "https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf"
        ],
        vector_db=PgVector(table_name=table_name, db_url=vector_db_url),
        chunking_strategy=AgenticChunking(),
    )

    # This is a blocking call, so run it in a threadpool to avoid blocking the event loop
    from fastapi.concurrency import run_in_threadpool

    await run_in_threadpool(
        knowledge_base.load,
        True,
    )  # recreate=False for incremental load

    agent = Agent(
        knowledge_base=knowledge_base,
        search_knowledge=True,
    )

    response = agent.print_response("What is this paper about?", markdown=True)
    return {"response": response}


"""
@app.post("/chunkie/")
def chunkie():
    # https://medium.com/@pymupdf/extracting-text-from-multi-column-pages-a-practical-pymupdf-guide-a5848e5899fe
    doc = pymupdf.open("./uploads/singh2018.pdf")
    out = open("./uploads/outputchunks.txt", "wb")
    for page in doc:
        text = page.get_text().encode("utf-8")
        out.write(text)
        out.write(bytes((12,)))
    out.close

    with open("./uploads/outputchunks.txt", "r") as f:
        pdf_data = f.read()

    print(pdf_data)

    chunker = RecursiveChunker()
    chunks = chunker(pdf_data)
    counter = 0
    chunk_dict = {}
    for chunk in chunks:
        print(f"Chunk: {chunk.text}")
        print(f"Tokens: {chunk.token_count}")
        chunk_dict[counter] = chunk.text
        counter += 1
    dict_out = open("./uploads/dict_out.txt", "w")
    dict_out.write(str(chunk_dict))
    return "Yay"


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
ollama_model = OpenAIModel(model_name="llama3.2:latest", provider=provider)

pdf_title_agent = Agent(
    ollama_model,
    system_prompt=(
        "You are a helpful assistant. Extract the title and authors of the document. "
        "Fix any formatting issues in the title (e.g., remove extra spaces, convert to title case, etc.). "
        "Your response must be a JSON object with the following format: "
        '{"title": "<title>", "authors": ["<author1>", "<author2>", ...]}. '
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
            f"What is the title and who are the authors of this document? {md_text[:300]}",
        )
        print(f"Model response: {data}")
        return data
    except Exception as e:
        print(f"Error: {e}")
        raise


# This Pydantic model is still useful for defining the expected structure if you parse the JSON
class FixedText(BaseModel):
    text: str


openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize the AsyncOpenAI client
# The base_url should point to the actual OpenAI API endpoint or your proxy
aclient = AsyncOpenAI(
    api_key=openai_api_key,
    # base_url="https://api.openai.com/v1" # Default, or your specific proxy if any
)

# The ollama_deepseek_model and fix_md_agent are no longer used for this endpoint
# You can remove them if they are not used elsewhere, or keep them for other purposes.
# ollama_deepseek_model = OpenAIModel(
#     model_name="llama3.1",
#     provider=provider,
# )
#
# fix_md_agent = Agent(
#     openai_model, # This was using the pydantic-ai OpenAIModel
#     system_prompt=(
#         "You are a helpful assistant. Fix any formatting issues in the markdown text. "
#         "Don't add text, remove text, or explain anything. Just fix Markdown formatting issues."
#         "Your response must be json with the following format: {'text': '<fixed text>'}. "
#         "Do not include any additional text or explanation. IMPORTANT: RETURN THE ENTIRE DOCUMENT."
#     ),
#     output_type=FixedText,
# )


# Helper function to split markdown by headings
def split_markdown_into_sections(md_text: str) -> List[str]:
    sections = []
    current_section_lines = []
    lines = md_text.splitlines(keepends=True)  # keepends preserves newline characters

    for line in lines:
        # Regex to identify a markdown heading (e.g., # Heading, ## Subheading)
        is_heading = re.match(r"^#{1,6}\s+", line)

        if is_heading:
            if (
                current_section_lines
            ):  # If there's content in the current section, finalize it
                sections.append("".join(current_section_lines))
            current_section_lines = [line]  # Start new section with the heading
        else:
            # If the document doesn't start with a heading, or for lines after a heading
            current_section_lines.append(line)

    if current_section_lines:  # Add the last accumulated section
        sections.append("".join(current_section_lines))

    return [section for section in sections if section.strip()]


@app.post("/fix_md_formatting/")
async def fix_md_formatting():
    input_file_path = "./uploads/singh2018.md"
    output_file_path = "./uploads/singh2018_fixed.md"

    try:
        with open(input_file_path, "r", encoding="utf-8") as f:  # Added encoding
            md_text = f.read()
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Input file not found: {input_file_path}"
        )

    print(f"Original MD TEXT length: {len(md_text)}")

    sections = split_markdown_into_sections(md_text)
    if not sections:
        return {"message": "No content found in the markdown file to process."}

    print(f"Split into {len(sections)} sections.")

    system_prompt_content = (
        "You are a helpful assistant. Fix any formatting issues in the markdown text provided. "
        "Don't add text, remove text, or explain anything. Just fix Markdown formatting issues for the given text segment. "
        "Your response must be a JSON object with a single key 'text' that contains the ENTIRE fixed markdown segment. "
        'Example: {"text": "<entire fixed markdown segment here>"}. '
        "Do not include any additional text or explanation outside this JSON structure."
    )

    all_fixed_markdown_parts = []
    processed_chunks_count = 0

    for i, section_text in enumerate(sections):
        print(
            f"Processing section {i+1}/{len(sections)}, length: {len(section_text)} chars"
        )
        if not section_text.strip():
            all_fixed_markdown_parts.append(
                section_text
            )  # Keep empty/whitespace sections as they are
            continue

        try:
            chat_completion = await aclient.chat.completions.create(
                model="gpt-4.1",  # Ensure this model name is correct
                messages=[
                    {"role": "system", "content": system_prompt_content},
                    {"role": "user", "content": section_text},
                ],
                max_tokens=25000,  # This now applies per chunk. Adjust if model's output limit is lower.
                # E.g., 4096 or 8192 might be more typical if sections are smaller.
                temperature=0.2,
                # response_format={"type": "json_object"} # Uncomment if your model/API supports this
            )

            response_content = chat_completion.choices[0].message.content

            try:
                data = json.loads(response_content)
                fixed_section_segment = data.get("text")
                if fixed_section_segment is None:
                    print(
                        f"Warning: LLM response JSON for section {i+1} did not contain 'text' key. Using original section text."
                    )
                    all_fixed_markdown_parts.append(
                        section_text
                    )  # Fallback to original
                else:
                    all_fixed_markdown_parts.append(fixed_section_segment)
                    processed_chunks_count += 1
            except json.JSONDecodeError:
                print(
                    f"Warning: Failed to decode JSON for section {i+1}: '{response_content[:200]}...'. Using original section text."
                )
                all_fixed_markdown_parts.append(section_text)  # Fallback to original

        except Exception as e_chunk:
            print(
                f"Error processing section {i+1}: {e_chunk}. Using original section text."
            )
            all_fixed_markdown_parts.append(
                section_text
            )  # Fallback to original section text

    final_fixed_markdown = "".join(all_fixed_markdown_parts)

    try:
        with open(output_file_path, "w", encoding="utf-8") as f:  # Added encoding
            f.write(final_fixed_markdown)
    except IOError as e:
        print(f"Error writing to output file: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error writing fixed markdown to file: {str(e)}"
        )

    return {
        "message": f"Markdown content processed ({processed_chunks_count}/{len(sections)} sections successfully formatted by LLM) and saved to {output_file_path}",
        "file_path": output_file_path,
        "total_sections": len(sections),
        "llm_formatted_sections": processed_chunks_count,
        "final_fixed_markdown_content_length": len(final_fixed_markdown),
    }


# this looks cool https://docling-project.github.io/docling/examples/export_figures/
"""
