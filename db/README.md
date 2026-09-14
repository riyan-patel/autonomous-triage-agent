# db

Postgres schema (with pgvector extension) and migrations.

## Status

`migrations/0001_init.sql` implements the full initial schema:
`installations`, `issues` (with a 384-dim pgvector `embedding` column and
an HNSW cosine index — see [`retrieval/`](../retrieval/README.md)),
`actions` (audit log), and `eval_labels` (evaluation ground truth).

`migrations/0002_add_reviews.sql` adds `reviews` (human approve/reject
decisions from the dashboard, build order step 7).

Mounted into `docker-entrypoint-initdb.d` via `docker-compose.yml`, so
`0001` runs automatically the first time the `postgres` container starts
against a fresh volume. It does **not** re-run against an existing volume
— every migration after `0001` needs to be applied by hand for now (no
migration runner wired up yet):

```bash
docker compose exec -T postgres psql -U triage -d triage_agent < db/migrations/0002_add_reviews.sql
```
