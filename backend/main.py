import os

import re
from typing import List
import json
import re

from fastapi import FastAPI, HTTPException

import pymupdf

from pydantic import BaseModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent


import openai
from openai import AsyncOpenAI

from chonkie import RecursiveChunker, SemanticChunker

from agno.agent import Agent as AgnoAgent
from agno.document.chunking.agentic import AgenticChunking
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.pgvector import PgVector

from helper_functions.parse import clean_extracted_text

from routers import reqs, testing

app = FastAPI(
    title="Requirements Engineering Agentic AI",
    version="0.1",
    description="Part of my Ph.D. dissertation.",
)
app.include_router(testing.router)
app.include_router(reqs.router)


UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads/")
os.makedirs(UPLOAD_DIR, exist_ok=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

provider = OpenAIProvider(base_url="http://host.docker.internal:11434/v1")
ollama_model = OpenAIModel(model_name="llama3.2:latest", provider=provider)
phi_model = OpenAIModel(model_name="phi3:14b", provider=provider)

parsing_agent = Agent(
    model=OpenAIModel(
        model_name="gpt-4.1", provider=OpenAIProvider(api_key=OPENAI_API_KEY)
    )
)


class RequirementOutput(BaseModel):
    requirements: List[str]


@app.post("/agentic_chunking/")
async def agentic_chunking():

    vector_db_url = "postgresql+psycopg2://user:password@vectordb:5432/vector_db"

    table_name = "test"

    knowledge_base = PDFUrlKnowledgeBase(
        urls=[
            "https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf"
        ],
        vector_db=PgVector(table_name=table_name, db_url=vector_db_url),
        chunking_strategy=AgenticChunking(),
    )

    knowledge_base.load(recreate=False)

    agent = AgnoAgent(
        knowledge=knowledge_base,
        search_knowledge=True,
    )

    response = agent.print_response("How do you build an agent?", markdown=True)
    return {"response": response}


open_ai_model = OpenAIModel(
    model_name="gpt-4.1", provider=OpenAIProvider(api_key=OPENAI_API_KEY)
)

requirements_agent = Agent(
    open_ai_model,
    system_prompt=(
        "You are an expert requirements engineer. Extract all requirements from the document and return them as a list of strings List[str]. Do not include any additional text or explanation but you can reformat the text to make it readable."
    ),
)


@app.post("/chunkie/")
def chunkie():
    # https://medium.com/@pymupdf/extracting-text-from-multi-column-pages-a-practical-pymupdf-guide-a5848e5899fe
    doc = pymupdf.open("./uploads/20090110-fua-spec-v1.1.pdf")
    out = open("./uploads/routputchunks.txt", "wb")
    for page in doc:
        text = page.get_text().encode("utf-8")
        out.write(text)
        out.write(bytes((12,)))
    out.close

    with open("./uploads/routputchunks.txt", "r") as f:
        pdf_data = f.read()

    clean_extracted_text(pdf_data)

    chunker = RecursiveChunker()
    # chunker = SemanticChunkerChunker(threshold=0.5, min_sentences=1)
    chunks = chunker(pdf_data)
    counter = 0
    chunk_dict = {}
    for chunk in chunks:
        chunk_dict[counter] = chunk.text
        counter += 1
        # requirements = requirements_agent.run_sync(chunk)
        # print(f"{requirements}")
    dict_out = open("./uploads/rdict_out.txt", "w")
    dict_out.write(str(chunk_dict))
    requirements_list = []
    for key in chunk_dict:
        if key <= 20 or key >= 30:
            pass
        requirements = requirements_agent.run_sync(chunk_dict[key])
        print(requirements)
        requirements_list.append(requirements)
    print(requirements_list)
    return "Yay"


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
