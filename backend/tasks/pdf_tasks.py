import os

# import uuid # No longer needed as file_path will be used as UUID
import psycopg2  # For database error handling
from celery_app import celery
from helper_functions.parse import parse_pdf
from db.conn import get_db_connection  # Import your DB connection function
import logging

logger = logging.getLogger(__name__)


@celery.task
def get_pdf_data_task(file_path: str):
    logger.info(f"Starting get_pdf_data_task for: {file_path}")
    parsed_data_from_helper = parse_pdf(file_path)
    logger.info(f"Parsed data from helper: {parsed_data_from_helper}")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Extract the base filename without extension to use as UUID
        base_name = os.path.basename(file_path)
        paper_uuid_from_path, _ = os.path.splitext(base_name)

        # 1. Insert into papers table
        paper_title = parsed_data_from_helper.get("title")  # Assumes 'title' key exists

        insert_paper_query = """
        INSERT INTO papers (uuid, title, original_file_path)
        VALUES (%s, %s, %s) RETURNING uuid;
        """
        # Use the extracted paper_uuid_from_path as the uuid, and full file_path for original_file_path
        cursor.execute(
            insert_paper_query, (paper_uuid_from_path, paper_title, file_path)
        )
        paper_id_tuple = cursor.fetchone()
        if not paper_id_tuple:
            logger.error(f"Failed to insert paper for {file_path}. No ID returned.")
            raise Exception(f"Failed to insert paper for {file_path}")

        # paper_id now correctly holds the extracted uuid (e.g., e7727547c53448c68e437d8880fcc196)
        paper_id = paper_id_tuple[0]
        logger.info(
            f"Inserted paper with UUID: {paper_id} for original file: {file_path}"
        )

        # 2. Insert authors and link to paper
        author_names = parsed_data_from_helper.get("authors", [])
        if not isinstance(author_names, list):
            logger.warning(
                f"Authors data for {file_path} is not a list: {author_names}. Skipping author insertion."
            )
            author_names = []

        for author_name in author_names:
            if not isinstance(author_name, str) or not author_name.strip():
                logger.warning(
                    f"Invalid or empty author name found: '{author_name}'. Skipping."
                )
                continue

            insert_author_query = """
            INSERT INTO authors (name) VALUES (%s)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id;
            """
            cursor.execute(insert_author_query, (author_name.strip(),))
            author_id_tuple = cursor.fetchone()
            if not author_id_tuple:
                logger.error(
                    f"Failed to insert or retrieve author: {author_name} for paper UUID {paper_id}"
                )
                continue
            author_id = author_id_tuple[0]
            logger.info(f"Processed author '{author_name}' with ID: {author_id}")

            insert_paper_author_query = """
            INSERT INTO paper_authors (paper_id, author_id)
            VALUES (%s, %s) ON CONFLICT (paper_id, author_id) DO NOTHING;
            """
            # paper_id here is the UUID from the papers table (e.g., e7727547c53448c68e437d8880fcc196)
            cursor.execute(insert_paper_author_query, (paper_id, author_id))
            logger.info(f"Linked paper UUID {paper_id} with author ID {author_id}")

        conn.commit()
        logger.info(
            f"Successfully inserted paper and author data into DB for: {file_path}"
        )

    except psycopg2.Error as e:
        logger.error(f"Database error during get_pdf_data_task for {file_path}: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in get_pdf_data_task for {file_path}: {e}", exc_info=True
        )
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return parsed_data_from_helper
