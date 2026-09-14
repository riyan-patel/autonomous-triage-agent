# worker

Queue worker (RQ) that pulls triage jobs off Redis, drives the agent
core, and handles retries/backoff/idempotency via delivery ID dedupe.

## Status

Implemented: the RQ worker process, and `process_issue_event` — the job
entry point webhook-ingress enqueues by import path. It validates the
payload shape and calls into a pipeline stub (`pipeline.py`).

Not yet implemented: the actual triage pipeline (retrieval, LLM call,
MCP tool actions — build order steps 3-5). `pipeline.run_triage` is a
placeholder that returns `status="not_implemented"` so the queue/worker
plumbing is provable end-to-end before the agent logic exists.

Retry policy (3 attempts, 10s/30s/60s backoff) is configured at enqueue
time in `webhook-ingress/app/queue.py` (`RETRY_POLICY`) and applies to
transient failures — an exception raised out of `process_issue_event`.
A malformed payload (missing `issue`/`repository` fields) is *not*
treated as retryable: it's logged and returned as
`{"status": "invalid_payload"}` instead of raised, since retrying a
permanently-bad payload would just burn all 3 attempts on a guaranteed
failure.

## Local development

```bash
cd worker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# run the test suite
pytest

# run the worker against real Redis (docker compose up -d redis)
export REDIS_URL=redis://localhost:6379/0
python -m worker.main   # run from the repo root, not from worker/
```

Note: the worker is imported as the dotted path `worker.jobs` (matching
what webhook-ingress enqueues by name), so `python -m worker.main` must
be run with the repo root on `PYTHONPATH` — running it from inside the
`worker/` directory itself won't resolve the package correctly.
