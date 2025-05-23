import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Generator

# --- Configuration ---
# Read database URLs from environment variables defined in docker-compose.yml
# Ensure these environment variables are set correctly in your docker-compose.yml
STANDARD_DATABASE_URL = os.getenv("DATABASE_URL")
VECTOR_DATABASE_URL = os.getenv("VECTOR_DATABASE_URL")

if not STANDARD_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set.")
if not VECTOR_DATABASE_URL:
    raise ValueError("VECTOR_DATABASE_URL environment variable not set.")

# --- Standard Database Connection ---


def get_db_connection():
    """
    Establishes and returns a connection to the standard PostgreSQL database.
    """
    try:
        # Connect to the standard database using the URL
        conn = psycopg2.connect(STANDARD_DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to standard database: {e}")
        # In a real application, you might want to log this error and handle it more gracefully
        raise


def get_db_cursor(conn) -> psycopg2.extensions.cursor:
    """
    Returns a cursor for the given database connection.
    Using RealDictCursor to get results as dictionaries.
    """
    return conn.cursor(cursor_factory=RealDictCursor)


# Dependency function for standard database connection
def get_db_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    FastAPI dependency that provides a connection to the standard database.
    Ensures the connection is closed after the request.
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


# Dependency function for standard database cursor
def get_db_cursor_dependency(
    # conn: psycopg2.extensions.connection = Depends(get_db_conn), # Remove Depends here
) -> Generator[psycopg2.extensions.cursor, None, None]:
    """
    FastAPI dependency that provides a cursor for the standard database.
    This function itself should not use Depends in its signature.
    It's intended to be used WITH Depends in a route.
    To use this, a route would look like:
    async def my_route(cursor: psycopg2.extensions.cursor = Depends(get_db_cursor_dependency)):
        pass
    And FastAPI would first call get_db_conn, then pass its result to this function.
    However, the typical pattern is to depend on get_db_conn and then get a cursor.
    Let's simplify this to match common patterns or adjust how it's used.

    A more common pattern for a cursor dependency:
    """
    conn = get_db_connection()  # Or, if you want to use the get_db_conn generator:
    # This function would need to be called within a route that
    # already has a 'conn' from 'Depends(get_db_conn)'
    # For a standalone cursor dependency that manages its own connection:
    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
    finally:
        if cursor:
            cursor.close()
        if conn:  # Ensure conn is closed if this function manages it
            conn.close()


# --- Vector Database Connection ---


def get_vector_db_connection():
    """
    Establishes and returns a connection to the pgvector database.
    The connection method is the same as a regular PostgreSQL database.
    """
    try:
        # Connect to the vector database using the URL
        conn = psycopg2.connect(VECTOR_DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to vector database: {e}")
        # In a real application, you might want to log this error and handle it more gracefully
        raise


def get_vector_db_cursor(conn) -> psycopg2.extensions.cursor:
    """
    Returns a cursor for the given vector database connection.
    Using RealDictCursor for dictionary results.
    """
    return conn.cursor(cursor_factory=RealDictCursor)


# Dependency function for vector database connection
def get_vector_db_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    FastAPI dependency that provides a connection to the vector database.
    Ensures the connection is closed after the request.
    """
    conn = get_vector_db_connection()
    try:
        yield conn
    finally:
        conn.close()


# Dependency function for vector database cursor
def get_vector_db_cursor_dependency(
    # conn: psycopg2.extensions.connection = Depends(get_vector_db_conn), # Remove Depends here
) -> Generator[psycopg2.extensions.cursor, None, None]:
    """
    FastAPI dependency that provides a cursor for the vector database.
    Manages its own connection for simplicity as a direct dependency.
    """
    conn = get_vector_db_connection()
    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# --- How to use in FastAPI Endpoints ---
#
# from fastapi import APIRouter, Depends, HTTPException
# from psycopg2.extensions import cursor as Psycopg2Cursor, connection as Psycopg2Connection
# # Import the cursor dependency functions
# from app.database import get_db_cursor_dependency, get_vector_db_cursor_dependency # Adjust import path as needed
#
# router = APIRouter()
#
# @router.get("/items/")
# def read_items(db_cursor: Psycopg2Cursor = Depends(get_db_cursor_dependency)):
#     # Execute a raw SQL query on the standard database
#     db_cursor.execute("SELECT id, name, description FROM items;")
#     items = db_cursor.fetchall()
#     return items
#
# @router.post("/items/")
# def create_item(item_data: Dict[str, Any], db_conn: Psycopg2Connection = Depends(get_db_conn)):
#     # Use the connection dependency for operations that require committing
#     db_cursor = db_conn.cursor() # Get a cursor from the connection
#     try:
#         # Example of an INSERT query
#         db_cursor.execute(
#             "INSERT INTO items (name, description) VALUES (%s, %s) RETURNING id;",
#             (item_data.get("name"), item_data.get("description"))
#         )
#         new_item_id = db_cursor.fetchone()['id']
#         db_conn.commit() # Commit the transaction
#         return {"id": new_item_id, **item_data}
#     except psycopg2.Error as e:
#         db_conn.rollback() # Rollback in case of error
#         raise HTTPException(status_code=500, detail=f"Database error: {e}")
#     finally:
#         db_cursor.close()
#
# @router.post("/vector_data/")
# def add_vector_data(data: Dict[str, Any], vector_db_conn: Psycopg2Connection = Depends(get_vector_db_conn)):
#     vector_db_cursor = vector_db_conn.cursor()
#     try:
#         # Example of inserting data with a vector
#         # Assuming you have a table 'vector_items' with a 'vector_embedding' column of type VECTOR
#         # The vector needs to be represented as a string like '[1.2, 3.4, 5.6]' for psycopg2
#         vector_embedding_str = str(data.get("embedding")) # Ensure embedding is a list of floats
#         vector_db_cursor.execute(
#             "INSERT INTO vector_items (name, vector_embedding) VALUES (%s, %s) RETURNING id;",
#             (data.get("name"), vector_embedding_str)
#         )
#         new_vector_item_id = vector_db_cursor.fetchone()['id']
#         vector_db_conn.commit()
#         return {"id": new_vector_item_id, **data}
#     except psycopg2.Error as e:
#         vector_db_conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Vector database error: {e}")
#     finally:
#         vector_db_cursor.close()
#
# @router.get("/vector_search/")
# def search_vector_data(query_vector: List[float], vector_db_cursor: Psycopg2Cursor = Depends(get_vector_db_cursor_dependency)):
#     try:
#         # Example of a vector similarity search using the '<=>' operator (cosine distance)
#         # The query vector also needs to be represented as a string
#         query_vector_str = str(query_vector)
#         vector_db_cursor.execute(
#             "SELECT id, name, vector_embedding, vector_embedding <=> %s AS distance FROM vector_items ORDER BY distance LIMIT 10;",
#             (query_vector_str,)
#         )
#         results = vector_db_cursor.fetchall()
#         return results
#     except psycopg2.Error as e:
#         raise HTTPException(status_code=500, detail=f"Vector database search error: {e}")
