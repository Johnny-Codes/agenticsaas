import re
import unicodedata
import pathlib
import logging

import pymupdf4llm

from agents.parse import pdf_metadata_agent

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


async def get_pdf_title(md_text: str):  # Make this async
    # The while loop here doesn't effectively retry due to the 'raise'
    # Consider a proper retry mechanism if needed, or simplify.
    try:
        # Assuming pdf_metadata_agent.run is an async method
        data = await pdf_metadata_agent.run_sync(  # Add await here
            f"What is the title and who are the authors of this document? {md_text[:1000]}",
        )
        logger.info(f"Model response: {data}")  # Use logger if you have it
        return data
    except Exception as e:
        logger.error(f"Error in get_pdf_title: {e}", exc_info=True)  # Use logger
        raise


async def parse_pdf(file_path: str):  # Make this async
    logger.info(f"Starting PDF parsing for: {file_path}")
    md_text = pymupdf4llm.to_markdown(file_path)  # This is synchronous
    md_file_path = f"{file_path[:-4]}.md"
    pathlib.Path(md_file_path).write_bytes(md_text.encode())
    logger.info(f"Markdown content saved to: {md_file_path}")

    pdf_data = await get_pdf_title(md_text)  # Add await here
    logger.info(f"Successfully extracted pdf_data for {file_path}: {pdf_data}")

    return f"{pdf_data}"
