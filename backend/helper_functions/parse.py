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


def get_pdf_metadata(
    md_text: str, max_retries: int = 3, retry_delay: int = 5
):  # Added retry parameters
    """
    Calls the PDF metadata agent with the provided markdown text, logs the raw response,
    and retries on failure.
    """
    attempt = 0
    last_exception = None
    while attempt < max_retries:
        logger.info(
            f"get_pdf_metadata: Attempt {attempt + 1}/{max_retries}. Calling agent with prompt based on md_text snippet (first 500 chars)."
        )
        try:
            agent_run_result = pdf_metadata_agent.run_sync(md_text[:500])
            logger.info(f"agent response is \n {agent_run_result}")
            content = agent_run_result.output
            logger.info(f"CONTENT: {content}")

            # Check if content is not None and has title or authors, indicating a good response
            # This check might need to be adjusted based on what a "good response" means for your PDFData object
            if content and (hasattr(content, "title") or hasattr(content, "authors")):
                # Convert the PDFData object to a dictionary
                if hasattr(content, "model_dump"):
                    return content.model_dump()  # For Pydantic v2+
                elif hasattr(content, "dict"):
                    return content.dict()  # For Pydantic v1
                else:
                    logger.error(
                        "PDFData object does not have .model_dump() or .dict() method but was considered valid."
                    )
                    # This case should ideally not be hit if the content check above is robust
                    raise TypeError(
                        "Cannot convert PDFData object to dictionary despite initial validation."
                    )
            else:
                logger.warning(
                    f"Agent returned empty or incomplete content on attempt {attempt + 1}: {content}"
                )
                # This will lead to a retry if content is not satisfactory

            # If the agent returns something that isn't an exception but isn't valid,
            # we might want to treat it as a failure to trigger a retry.
            # For now, we assume pydantic_ai will raise an exception for most failures.
            # If it successfully returns but with empty/invalid data, the above 'if content' check handles it.

        except pydantic_ai_exceptions.UnexpectedModelBehavior as e:
            last_exception = e
            logger.warning(
                f"get_pdf_metadata: Attempt {attempt + 1} failed with UnexpectedModelBehavior: {e}. Retrying in {retry_delay} seconds..."
            )
            time.sleep(retry_delay)
        except Exception as e:  # Catch other potential exceptions during the agent call
            last_exception = e
            logger.error(
                f"get_pdf_metadata: Attempt {attempt + 1} failed with an unexpected error: {e}. Retrying in {retry_delay} seconds..."
            )
            time.sleep(retry_delay)

        attempt += 1

    logger.error(
        f"get_pdf_metadata: Failed after {max_retries} attempts. Last exception: {last_exception}"
    )
    if last_exception:
        raise last_exception
    else:
        # This case would be if all retries resulted in non-exception but "bad" (e.g. empty) content
        raise Exception(
            f"Failed to get valid PDF metadata after {max_retries} attempts. Last content was empty or invalid."
        )


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
