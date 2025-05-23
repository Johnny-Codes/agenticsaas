import re
import unicodedata
import pathlib
import logging
import time
import json  # For parsing JSON response from agent

import pymupdf4llm

from agents.parse import pdf_metadata_agent
from pydantic_ai import (
    exceptions as pydantic_ai_exceptions,
)

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


def get_pdf_metadata(
    md_text: str, max_retries: int = 5, delay_seconds: int = 2
) -> dict:
    """
    Tries to get PDF title and a list of authors using an agent, with retries.
    Returns a dictionary: {"title": "...", "authors": ["...", "..."]}.
    """
    # Adjust this prompt to encourage your agent to return structured JSON
    prompt = (
        f"Extract the title and a list of all authors from the following document text. "
        f"Respond ONLY with a JSON object with two keys: 'title' (a string) and 'authors' (a list of strings). "
        f"Document text snippet: {md_text[:1500]}"  # Increased snippet size
    )

    for attempt in range(max_retries):
        try:
            raw_agent_response = pdf_metadata_agent.run_sync(prompt)
            logger.info(
                f"Agent raw response on attempt {attempt + 1}: {raw_agent_response}"
            )

            if not raw_agent_response:
                logger.warning(f"Attempt {attempt + 1}: Agent returned empty data.")
                if attempt + 1 == max_retries:
                    raise Exception("Agent returned empty data after max retries.")
                time.sleep(delay_seconds * (attempt + 1))
                continue

            # Attempt to parse the response as JSON
            # LLMs sometimes wrap JSON in markdown code blocks
            cleaned_response = raw_agent_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            parsed_data = json.loads(cleaned_response.strip())

            if (
                isinstance(parsed_data, dict)
                and "title" in parsed_data
                and isinstance(parsed_data["title"], str)
                and "authors" in parsed_data
                and isinstance(parsed_data["authors"], list)
                and all(isinstance(author, str) for author in parsed_data["authors"])
            ):
                logger.info(f"Successfully parsed metadata: {parsed_data}")
                return parsed_data
            else:
                logger.warning(
                    f"Attempt {attempt + 1}: Parsed data not in expected format: {parsed_data}"
                )
                if attempt + 1 == max_retries:
                    raise ValueError(
                        "Parsed data not in expected format after max retries."
                    )
                time.sleep(delay_seconds * (attempt + 1))

        except json.JSONDecodeError as e:
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed to parse JSON: {e}. Response: {raw_agent_response}"
            )
            if attempt + 1 == max_retries:
                raise
            time.sleep(delay_seconds * (attempt + 1))
        except pydantic_ai_exceptions.UnexpectedModelBehavior as e:
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed due to UnexpectedModelBehavior: {e}"
            )
            if attempt + 1 == max_retries:
                raise
            time.sleep(delay_seconds * (attempt + 1))
        except Exception as e:
            logger.error(
                f"Attempt {attempt + 1}/{max_retries} failed with an unexpected error: {e}",
                exc_info=True,
            )
            if attempt + 1 == max_retries:
                raise
            time.sleep(delay_seconds)

    logger.error(f"Failed to get PDF metadata after {max_retries} attempts.")
    raise Exception(f"Failed to get PDF metadata after {max_retries} attempts.")


def parse_pdf(file_path: str) -> dict:
    logger.info(f"Starting PDF parsing for: {file_path}")
    md_text = pymupdf4llm.to_markdown(file_path)
    # Saving the .md file is optional if you only need the metadata for the DB
    # md_file_path = f"{file_path[:-4]}.md"
    # pathlib.Path(md_file_path).write_bytes(md_text.encode())
    # logger.info(f"Markdown content saved to: {md_file_path}")

    pdf_metadata = get_pdf_metadata(md_text)  # Changed from get_pdf_title
    logger.info(f"Successfully extracted pdf_metadata for {file_path}: {pdf_metadata}")

    return pdf_metadata  # Return the dictionary
