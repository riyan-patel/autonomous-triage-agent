-- Build order step 4: full initial schema.
CREATE EXTENSION IF NOT EXISTS vector;

-- One row per GitHub App installation (a repo or org that installed the app).
CREATE TABLE installations (
    id                     SERIAL PRIMARY KEY,
    github_installation_id BIGINT NOT NULL UNIQUE,
    account_login          TEXT NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Embedding dimension matches the default local embedder
-- (sentence-transformers/all-MiniLM-L6-v2, see retrieval/embeddings.py).
-- Changing embedding models requires a migration to resize this column.
CREATE TABLE issues (
    id               SERIAL PRIMARY KEY,
    installation_id  INTEGER REFERENCES installations(id),
    repo_full_name   TEXT NOT NULL,
    issue_number     INTEGER NOT NULL,
    title            TEXT NOT NULL,
    body             TEXT NOT NULL DEFAULT '',
    state            TEXT NOT NULL DEFAULT 'open',
    embedding        vector(384),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (repo_full_name, issue_number)
);

-- HNSW over IVFFlat: no ANALYZE/list-count tuning needed and it stays
-- accurate on a small, incrementally-growing table (an early-stage repo's
-- issue count), unlike IVFFlat which needs list-count ~ sqrt(row count).
CREATE INDEX issues_embedding_cosine_idx
    ON issues USING hnsw (embedding vector_cosine_ops);

-- Full audit log of every decision the agent makes - the eval harness
-- (build order step 8) reads from this table.
CREATE TABLE actions (
    id           SERIAL PRIMARY KEY,
    issue_id     INTEGER NOT NULL REFERENCES issues(id),
    delivery_id  TEXT NOT NULL,
    action_type  TEXT NOT NULL,
    payload      JSONB NOT NULL DEFAULT '{}',
    confidence   REAL,
    dry_run      BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (delivery_id, action_type)
);

-- Ground truth for evaluation (build order step 8): human-labeled correct
-- outcome for an issue, compared against what the agent actually did.
CREATE TABLE eval_labels (
    id                       SERIAL PRIMARY KEY,
    issue_id                 INTEGER NOT NULL REFERENCES issues(id),
    ground_truth_labels      TEXT[] NOT NULL DEFAULT '{}',
    ground_truth_duplicate_of INTEGER,
    notes                    TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);
