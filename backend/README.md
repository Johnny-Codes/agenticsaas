This is the backend for the agentic saas project using FastAPI, PG, PGVector, Pydantic AI, Agno AI


## Parsing PDFs

Using Chonkie and pymupdf4llm Workflow:
1. Parse PDF (pymupdf)
2. Clean text (./helper_functions/parse.py)
3. Chunk (chonkie)

To Do:

- [ ] Multi modal - get images, tables, figures, etc.
- [ ] Extract references
- [ ] Celery for background tasks