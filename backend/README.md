This is the backend for the agentic saas project using FastAPI, PG, PGVector, Pydantic AI, Agno AI, Neo4j


## Parsing PDFs

Using Chonkie and pymupdf4llm Workflow:
1. Parse PDF (pymupdf)
2. Clean text (./helper_functions/parse.py)
3. Chunk (chonkie)

To Do:

- [ ] Multi modal - get images, tables, figures, etc.
    - Figure out how to do multi_column
- [ ] Extract references
- [ ] Celery for background tasks