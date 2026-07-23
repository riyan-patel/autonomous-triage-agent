# webhook-ingress

FastAPI service that receives GitHub `issues.*` webhooks, verifies the
HMAC-SHA256 signature (`X-Hub-Signature-256`), and enqueues a job for the
worker. Responds fast (<10s) per GitHub's webhook timeout.

Not yet implemented — see build order step 1 in `docs/ARCHITECTURE.md`.
