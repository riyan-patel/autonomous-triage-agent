# worker

Queue worker (RQ) that pulls triage jobs off Redis, drives the agent
core, and handles retries/backoff/idempotency via delivery ID dedupe.

Not yet implemented — see build order step 2 in `docs/ARCHITECTURE.md`.
