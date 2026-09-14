# retrieval

Embedding + indexing pipeline. Backfills existing issues into pgvector,
embeds new issues at triage time, and runs k-NN cosine search for
duplicate detection and RAG context. Also handles reviewer routing via
CODEOWNERS.

## Status

Implemented:

- `embeddings.py` — `Embedder` interface; `SentenceTransformerEmbedder` is
  the default (local, no API key, `sentence-transformers/all-MiniLM-L6-v2`,
  384-dim) so retrieval works independent of whichever LLM provider is
  configured for reasoning.
- `models.py` / `db.py` — SQLAlchemy ORM mirroring `db/migrations/0001_init.sql`
  (`issues`, `actions`, `eval_labels`, `installations`), with `issues.embedding`
  as a pgvector column indexed with HNSW (cosine ops).
- `indexer.py` — `index_issue(...)`: embed title+body, upsert by
  `(repo_full_name, issue_number)`. Used for both the install-time backfill
  and per-issue indexing at triage time.
- `duplicates.py` — `find_similar_issues(...)`: k-NN cosine search scoped
  to one repo, for duplicate candidates and RAG context.
- `reviewer_routing.py` — parses a CODEOWNERS file (last-match-wins, per
  GitHub's own rule) and matches path-like tokens extracted from issue
  text against it.

Not yet implemented: the recent-commit-author fallback for reviewer
routing (needs the GitHub API — lands when this is wired into agent-core,
build order step 5), and the install-time backfill script itself (lands
in `scripts/` once there's a GitHub client to pull existing issues from).

## Local development

```bash
cd retrieval
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# needs Postgres with the migration applied - fresh volume runs it
# automatically via docker-entrypoint-initdb.d
docker compose up -d postgres   # from the repo root

pytest   # DB-backed tests skip cleanly if Postgres isn't reachable
```

Tests never `commit()` — each test's session is rolled back on teardown,
so the schema stays clean between runs without manual cleanup.
