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

## Database and Migrations

Using yoyo for migrations. `yoyo apply --database "$DATABASE_URL" ./migrations`

## Neo4J

Clearing neo4j while testing, in neo4j console use `MATCH (n) DETACH DELETE n`

For showing everything in neo4j:
```
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m
```