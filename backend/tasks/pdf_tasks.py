import os
from celery_app import celery
from helper_functions.parse import parse_pdf
from db.conn import (
    get_db_connection,
)  # Assuming this is your function to get a raw psycopg2 conn
import psycopg2  # For error handling
import logging

logger = logging.getLogger(__name__)


@celery.task
def get_pdf_data_task(file_path: str):
    try:
        logger.info(f"Starting get_pdf_data_task for: {file_path}")
        # parse_pdf now returns a dictionary: {"title": "...", "authors": ["...", "..."]}
        pdf_metadata = parse_pdf(file_path)

        title = pdf_metadata.get("title", "Title not found")
        author_names = pdf_metadata.get("authors", [])

        # Extract UUID from file_path (assuming filename is UUID.pdf)
        file_name_with_ext = os.path.basename(file_path)
        paper_uuid = os.path.splitext(file_name_with_ext)[0]

        conn = None
        try:
            conn = get_db_connection()  # Get a connection from your conn.py
            cursor = conn.cursor()

            # 1. Insert into papers table
            cursor.execute(
                """
                INSERT INTO papers (uuid, title, original_file_path)
                VALUES (%s, %s, %s)
                ON CONFLICT (uuid) DO UPDATE SET
                    title = EXCLUDED.title,
                    original_file_path = EXCLUDED.original_file_path
                RETURNING id;
                """,
                (paper_uuid, title, file_path),
            )
            paper_id_tuple = cursor.fetchone()
            if not paper_id_tuple:
                # This should not happen if RETURNING id is used and insert/update is successful
                conn.rollback()
                logger.error(f"Failed to insert or update paper with UUID {paper_uuid}")
                raise Exception(f"Failed to get paper_id for UUID {paper_uuid}")
            paper_id = paper_id_tuple[0]
            logger.info(
                f"Upserted paper_id: {paper_id} with UUID: {paper_uuid}, Title: {title}"
            )

            # 2. Insert authors and link to paper
            author_ids = []
            for author_name in author_names:
                if not author_name or not author_name.strip():
                    logger.warning(
                        f"Skipping empty author name for paper UUID {paper_uuid}"
                    )
                    continue

                # Insert author if not exists, get id
                cursor.execute(
                    """
                    INSERT INTO authors (name) VALUES (%s)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name -- Or DO NOTHING if preferred
                    RETURNING id;
                    """,
                    (author_name.strip(),),
                )
                author_id_tuple = cursor.fetchone()
                if not author_id_tuple:
                    conn.rollback()
                    logger.error(
                        f"Failed to insert or update author: {author_name.strip()}"
                    )
                    raise Exception(
                        f"Failed to get author_id for {author_name.strip()}"
                    )
                author_id = author_id_tuple[0]
                author_ids.append(author_id)
                logger.info(
                    f"Upserted author: '{author_name.strip()}' with ID: {author_id}"
                )

                # 3. Link author to paper in paper_authors table
                cursor.execute(
                    """
                    INSERT INTO paper_authors (paper_id, author_id) VALUES (%s, %s)
                    ON CONFLICT (paper_id, author_id) DO NOTHING;
                    """,
                    (paper_id, author_id),
                )
                logger.info(f"Linked paper_id: {paper_id} with author_id: {author_id}")

            conn.commit()
            logger.info(
                f"Successfully saved metadata for paper UUID {paper_uuid} to database."
            )
            return {
                "status": "success",
                "paper_id": paper_id,
                "uuid": paper_uuid,
                "title": title,
                "authors": author_names,
            }

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error processing {file_path}: {e}", exc_info=True)
            raise  # Re-raise to mark task as failed
        except Exception as e:
            if conn:
                conn.rollback()  # Rollback on any other error during DB operations
            logger.error(f"Unexpected error processing {file_path}: {e}", exc_info=True)
            raise
        finally:
            if conn:
                if cursor:  # Ensure cursor is defined before trying to close
                    cursor.close()
                conn.close()

    except Exception as e:
        logger.error(f"Failed get_pdf_data_task for {file_path}: {e}", exc_info=True)
        raise  # Re-raising the exception will mark the task as FAILED in Celery
