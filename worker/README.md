# worker

Queue worker (RQ) that pulls triage jobs off Redis, drives the agent
core, and handles retries/backoff/idempotency via delivery ID dedupe.

## Status

Implemented: the full pipeline. `jobs.process_issue_event` validates the
payload and calls `pipeline.run_triage`, which wires together:

1. **retrieval** — embeds the issue (local `sentence-transformers` model),
   upserts it into Postgres/pgvector, and runs k-NN cosine search for
   similar/duplicate issues in the same repo.
2. **agent-core** — builds the prompt from the issue + retrieved context +
   a static default label taxonomy, calls the LLM for structured output,
   and applies the confidence-gated act-vs-escalate policy.
3. **mcp-server** — on an "act" decision, calls `apply_labels`,
   `post_comment`, `assign_reviewer`, `link_duplicate` as appropriate
   (dry-run by default, so safe without a GitHub token).

`pipeline.run_triage` takes `retrieval_fn`, `llm_client`, `act_fn`, and
`audit_fn` as optional injectable seams (defaulting to the real
implementations above), so tests exercise the orchestration logic with
fakes instead of needing a live DB, model, or API key.
`tests/test_pipeline_live.py` is the exception — it exercises the *real*
retrieval layer, mcp-server, and audit write (only the LLM call is
faked, since no `ANTHROPIC_API_KEY` is configured here) to prove the
cross-package wiring genuinely works, not just each package in
isolation. It skips cleanly if Postgres isn't reachable.

Guardrails/reliability (build order step 6), on top of what step 2/3
already had (retry-with-backoff at enqueue, no-spam idempotency):

- **Audit log** — every triage decision (act or escalate) is written to
  `actions` via `_default_audit`, keyed by `(delivery_id, action_type)` so
  a retried job re-recording the same decision is a DB-level no-op too.
  This is also the data source the eval harness (step 8) will read from.
- **GitHub API rate-limit backoff** — lives in mcp-server (see its
  README): `GitHubClient._call` retries 403/429 honoring `Retry-After`.
- **Dead-letter visibility** (`dead_letter.py`) — `list_dead_letters(...)`
  surfaces jobs RQ parked in its `FailedJobRegistry` after exhausting
  retries, in a structured form instead of requiring someone to poke at
  Redis directly.

Not yet implemented: per-repo label taxonomy (currently a static default —
fetching a repo's real labels needs a GitHub API call not yet in
mcp-server's tool surface) and the recent-commit-author reviewer fallback.

### A real bug this caught

mcp-server, agent-core, and retrieval live in sibling directories with
hyphens in their names (`mcp-server/mcp_server`, `agent-core/agent_core`),
so `pipeline.py` bootstraps `sys.path` to make them importable. Wiring
this up live also surfaced that RQ's default `Worker` forks a subprocess
per job — which either reloads the embedding model on every single job,
or on macOS crashes outright (`SIGABRT`, an Objective-C fork-safety guard
tripping when the forked child touches PyTorch/Accelerate). `main.py`
uses `SimpleWorker` (no fork-per-job) instead, which fixes both: the
pipeline's embedder/DB engine/LLM client singletons actually stay warm
across jobs.

## Local development

```bash
cd worker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# run the test suite (needs Postgres up for test_pipeline_live.py, which
# skips cleanly if it isn't - docker compose up -d postgres from repo root)
pytest

# run the worker for real (needs Postgres + Redis up)
export DATABASE_URL=postgresql+psycopg://triage:triage@localhost:5432/triage_agent
export REDIS_URL=redis://localhost:6379/0
export ANTHROPIC_API_KEY=...   # required for a real triage decision
python -m worker.main   # run from the repo root, not from worker/
```

Without `ANTHROPIC_API_KEY` set, the worker still embeds/indexes the
issue and finds similar issues, then fails cleanly at the LLM call - a
useful way to sanity-check the retrieval half of the pipeline without an
API key.
