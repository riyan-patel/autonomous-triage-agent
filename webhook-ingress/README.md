# webhook-ingress

FastAPI service that receives GitHub `issues.*` webhooks, verifies the
HMAC-SHA256 signature (`X-Hub-Signature-256`), and enqueues a job for the
worker. Responds fast (<10s) per GitHub's webhook timeout.

## Status

Implemented: signature verification, event/action filtering, RQ-based
enqueue with delivery-ID idempotency (a redelivered webhook is a no-op).

Not yet implemented: the worker that actually consumes the queue
(`worker.jobs.process_issue_event` — build order step 2) and a persistent
idempotency store in Postgres (currently relies on RQ's job-ID uniqueness
in Redis, which is enough for now but isn't durable across a Redis flush).

## Endpoints

- `GET /healthz` — liveness check.
- `POST /webhooks/github` — GitHub webhook receiver. Verifies the
  signature, then for `issues` events with `action` in `opened`/`edited`,
  enqueues a job onto the `triage` Redis queue keyed by the GitHub
  delivery ID. All other events/actions are acknowledged with `202` and
  dropped. Returns `401` on a bad/missing signature, `400` on a missing
  delivery ID or malformed JSON.

## Local development

```bash
cd webhook-ingress
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# run the test suite (uses fakeredis, no real Redis needed)
pytest

# run the service against real Redis (docker compose up -d redis)
export GITHUB_WEBHOOK_SECRET=dev-secret
export REDIS_URL=redis://localhost:6379/0
uvicorn app.main:app --reload --port 8000
```

To point a real GitHub App webhook at a local instance, tunnel port 8000
(e.g. `ngrok http 8000`) and set the webhook URL to
`https://<tunnel>/webhooks/github` with the same secret as
`GITHUB_WEBHOOK_SECRET`.
