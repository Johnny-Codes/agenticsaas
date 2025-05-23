import re
import unicodedata
import pathlib
import logging
import asyncio  # Keep for context, but sleep will be time.sleep
import time  # Import time for synchronous sleep

import pymupdf4llm

from agents.parse import pdf_metadata_agent
from pydantic_ai import (
    exceptions as pydantic_ai_exceptions,
)  # Import pydantic-ai exceptions

logger = logging.getLogger(__name__)


def clean_extracted_text(text: str) -> str:
    """
    Applies a series of robust post-processing steps to text extracted from PDFs
    to clean up common parsing artifacts for NLP tasks.

    Args:
        text (str): The raw text string extracted from a PDF.

    Returns:
        str: The cleaned text string.
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


def get_pdf_title(
    md_text: str, max_retries: int = 5, delay_seconds: int = 2
):  # Changed to def
    """
    Tries to get PDF title and authors using an agent, with retries.
    """
    for attempt in range(max_retries):
        try:
            # Assuming pdf_metadata_agent has a synchronous 'run_sync' method
            # or that 'run' behaves synchronously if not awaited (less common for true async).
            # Adjust if your agent's synchronous method is different.
            data = pdf_metadata_agent.run_sync(  # Changed to run_sync (or your agent's sync equivalent)
                f"What is the title and who are the authors of this document? {md_text[:1000]}",
            )
            logger.info(f"Model response on attempt {attempt + 1}: {data}")
            if data:
                return data
        except pydantic_ai_exceptions.UnexpectedModelBehavior as e:
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed due to UnexpectedModelBehavior: {e}"
            )
            if attempt + 1 == max_retries:
                logger.error(f"Exceeded max retries ({max_retries}) for get_pdf_title.")
                raise
            time.sleep(delay_seconds * (attempt + 1))  # Changed to time.sleep
        except Exception as e:
            logger.error(
                f"Attempt {attempt + 1}/{max_retries} failed with an unexpected error: {e}",
                exc_info=True,
            )
            if attempt + 1 == max_retries:
                logger.error(
                    f"Exceeded max retries ({max_retries}) for get_pdf_title after unexpected error."
                )
                raise
            time.sleep(delay_seconds)  # Changed to time.sleep

    logger.error(f"Failed to get PDF title after {max_retries} attempts.")
    raise Exception(f"Failed to get PDF title after {max_retries} attempts.")


def parse_pdf(file_path: str):  # Changed to def
    logger.info(f"Starting PDF parsing for: {file_path}")
    md_text = pymupdf4llm.to_markdown(file_path)  # This is already synchronous
    md_file_path = f"{file_path[:-4]}.md"
    pathlib.Path(md_file_path).write_bytes(md_text.encode())
    logger.info(f"Markdown content saved to: {md_file_path}")

    pdf_data = get_pdf_title(md_text)  # This is now a synchronous call
    logger.info(f"Successfully extracted pdf_data for {file_path}: {pdf_data}")

    return f"{pdf_data}"
