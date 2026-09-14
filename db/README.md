# db

Postgres schema (with pgvector extension) and migrations.

## Status

`migrations/0001_init.sql` implements the full initial schema:
`installations`, `issues` (with a 384-dim pgvector `embedding` column and
an HNSW cosine index — see [`retrieval/`](../retrieval/README.md)),
`actions` (audit log), and `eval_labels` (evaluation ground truth).

Mounted into `docker-entrypoint-initdb.d` via `docker-compose.yml`, so it
runs automatically the first time the `postgres` container starts against
a fresh volume. It does **not** re-run against an existing volume — a
schema change needs a new numbered migration file (`0002_...sql`), applied
by hand for now (no migration runner wired up yet).
