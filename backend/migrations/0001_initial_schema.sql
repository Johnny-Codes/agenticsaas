CREATE TABLE IF NOT EXISTS papers (
    uuid TEXT UNIQUE NOT NULL PRIMARY KEY,
    title TEXT,
    original_file_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS authors (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_authors (
    paper_id TEXT REFERENCES papers(uuid) ON DELETE CASCADE,
    author_id INTEGER REFERENCES authors(id) ON DELETE CASCADE,
    PRIMARY KEY (paper_id, author_id)
);