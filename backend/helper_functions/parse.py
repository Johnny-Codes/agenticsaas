import re
import unicodedata
import pathlib
import logging
import json
import time  # Keep for potential future use, but not used in simplified version

import pymupdf4llm

from agents.parse import pdf_metadata_agent
from pydantic_ai import (  # Keep for context, agent might raise these
    exceptions as pydantic_ai_exceptions,
)


logger = logging.getLogger(__name__)


def clean_extracted_text(text: str) -> str:
    """
    Applies a series of robust post-processing steps to text extracted from PDFs
    to clean up common parsing artifacts for NLP tasks.
    """
    if not isinstance(text, str):
        return ""

    text = re.sub(r"^\d+:\s*\'?", "", text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"([a-zA-Z])-\s+([a-zA-Z])", r"\1\2", text)
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def get_pdf_metadata(md_text: str):  # Return type will be whatever agent returns
    """
    Calls the PDF metadata agent with the provided markdown text and logs the raw response.
    """

    logger.info(
        f"get_pdf_metadata: Calling agent with prompt based on md_text snippet (first 1500 chars)."
    )

    agent_run_result = pdf_metadata_agent.run_sync(md_text[:500])
    logger.info(f"agent response is \n {agent_run_result}")
    content = agent_run_result.output
    logger.info(f"CONTENT: {content}")
    # Convert the PDFData object to a dictionary
    if hasattr(content, "model_dump"):
        return content.model_dump()  # For Pydantic v2+
    elif hasattr(content, "dict"):
        return content.dict()  # For Pydantic v1
    else:
        # Fallback or error handling if it's not a known Pydantic model structure
        logger.error("PDFData object does not have .model_dump() or .dict() method.")
        # Depending on requirements, you might raise an error or return the object as is,
        # or try another serialization method if applicable.
        # For now, let's raise an error if it cannot be converted.
        raise TypeError("Cannot convert PDFData object to dictionary")


def parse_pdf(file_path: str):  # Return type will be whatever get_pdf_metadata returns
    """
    Parses a PDF to markdown, then calls get_pdf_metadata to extract metadata.
    """
    logger.info(f"parse_pdf: Starting PDF parsing for: {file_path}")

    try:
        md_text = pymupdf4llm.to_markdown(file_path)
        md_file_name = f"{file_path[:-4]}.md"
        pathlib.Path(md_file_name).write_bytes(md_text.encode())
        logger.info(f"parse_pdf: Markdown content saved to: {md_file_name}")

        # Call the simplified get_pdf_metadata
        raw_metadata_result = get_pdf_metadata(md_text)

        logger.info(
            f"parse_pdf: Result from get_pdf_metadata for {file_path}: {raw_metadata_result}"
        )
        return raw_metadata_result

    except Exception as e:
        logger.error(
            f"parse_pdf: Error during PDF processing for {file_path}: {e}",
            exc_info=True,
        )
        raise
