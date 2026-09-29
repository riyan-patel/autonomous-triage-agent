# Autonomous GitHub Triage Agent

An always-on, autonomous AI agent that takes GitHub issue triage off a
maintainer's plate. The moment a new issue is filed, it reads it,
summarizes it, labels it, detects duplicates, suggests a reviewer, and
drafts a first response, through a standardized MCP tool layer, with a
web dashboard and a measured accuracy number.

## Why this exists

The LLM here is a commodity component that gets called; the actual
engineering is the system built around it: an event-driven backend, a
real retrieval pipeline, reliability guarantees, a standardized MCP tool
layer, and an evaluation harness that proves it works.

## What it does

On every new/updated issue, the agent autonomously:

1. **Summarizes** the issue in one line.
2. **Classifies** it: bug / feature / question / docs, plus severity.
3. **Labels** it using the repo's actual label taxonomy.
4. **Detects duplicates** by semantic similarity against existing issues.
5. **Suggests a reviewer/owner** based on code ownership / recent authors.
6. **Drafts a first-response comment**.
7. **Decides autonomously** whether to act (apply labels/comment) or
   escalate to a human when confidence is low.
8. Logs every action to a dashboard with a full audit trail.

Two operating modes: **suggest mode** (drafts everything, human approves)
and **autonomous mode** (acts directly on high-confidence items, escalates
the rest).

## Architecture

```
        GitHub repo
            │  (webhook: issues.opened / edited)
            ▼
   ┌─────────────────┐     enqueue     ┌──────────────┐
   │  Webhook Ingress │ ──────────────▶ │  Job Queue    │  (Redis / RQ)
   │  (FastAPI)       │  verify HMAC    │  + retries    │
   └─────────────────┘                 └──────┬───────┘
                                              │  worker pulls job
                                              ▼
                                   ┌────────────────────┐
                                   │   AGENT CORE       │
                                   │  perceive→reason→act│
                                   └───────┬────────────┘
                    ┌──────────────────────┼───────────────────────┐
                    ▼                      ▼                        ▼
          ┌──────────────┐       ┌──────────────────┐     ┌──────────────────┐
          │ Retrieval    │       │  LLM (reasoning)  │     │  MCP GitHub server│
          │ (vector DB + │       │  structured tool  │────▶│  tools: label,    │
          │  embeddings) │◀──────│  calls            │     │  comment, assign, │
          └──────────────┘       └──────────────────┘     │  link_duplicate   │
                    │                                       └────────┬─────────┘
                    ▼                                                ▼
          ┌──────────────┐                                  GitHub REST/GraphQL API
          │ Postgres     │  (issues, actions, audit log, eval labels)
          └──────┬───────┘
                 ▼
          ┌──────────────┐
          │  Dashboard   │  (Next.js: live queue, actions, metrics)
          └──────────────┘
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full technical
plan: component depth, reliability/safety engineering, and the evaluation
methodology.

## Proven live

Everything below was confirmed working against real infrastructure, not
mocks: a real (private) GitHub repo, a real LLM API, and the actual
Redis/RQ queue, not a direct function call standing in for it.

- **A real signed GitHub webhook**, HMAC-verified, flows through
  `webhook-ingress` → Redis/RQ → `worker` → real GitHub writes (labels,
  comment) on a live issue. Bad signatures are rejected (401); redelivering
  the same delivery ID is deduped at the queue level (no double-processing).
- **The LLM call is real** (Gemini, swappable to Claude via `LLM_PROVIDER`),
  with structured JSON output validated against the same schema either
  provider must satisfy.
- **Reviewer routing is grounded, not guessed**: the agent reads the
  repo's actual `CODEOWNERS` file and only assigns a reviewer when a real
  pattern match exists. Confirmed live: an issue mentioning `worker/jobs.py`
  correctly resolved to the right owner and was assigned on GitHub.
- **Label taxonomy is fetched from the real repo**, not a hardcoded list;
  it falls back to a small default set only if the repo has no labels or no
  token is configured.
- **The dashboard's Approve button actually executes**: clicking it
  triggers a real HTTP call to `webhook-ingress`, which enqueues a real
  worker job that calls mcp-server's tools against GitHub. Confirmed via
  a real approve click flowing through the real queue to a real GitHub
  write, with idempotency verified (re-clicking Approve doesn't double-act).
- Confidence gating is real: on a genuinely low-confidence issue, the agent
  escalates instead of acting, and nothing touches GitHub until a human
  approves it from the dashboard.

## Repo layout

| Path | Purpose |
|---|---|
| `webhook-ingress/` | FastAPI service: receives + HMAC-verifies GitHub webhooks, enqueues jobs |
| `worker/` | Queue worker: pulls jobs, drives the agent core, handles retries/idempotency |
| `mcp-server/` | MCP server exposing GitHub actions as standardized tools (`apply_labels`, `post_comment`, `assign_reviewer`, `link_duplicate`, `search_issues`) |
| `retrieval/` | Embedding + indexing pipeline, pgvector k-NN search for duplicates and reviewer routing |
| `agent-core/` | The reasoning loop: prompt construction, structured output, confidence-gated decision policy |
| `dashboard/` | Next.js dashboard: live triage queue with search/filter, a "Needs your review" section for escalated items, expandable per-issue detail, links out to the real GitHub issue, approve/reject that actually executes, and metrics |
| `eval/` | Evaluation harness: labeled benchmark + accuracy/precision/recall metrics |
| `db/` | Postgres schema + migrations |
| `scripts/` | One-off / operational scripts (backfill, seed data, etc.) |
| `docs/` | Architecture doc and design notes |

## Tech stack

| Layer | Choice |
|---|---|
| Backend / agent | Python, FastAPI |
| Queue | Redis + RQ |
| LLM | Swappable via `LLM_PROVIDER`: Anthropic (Claude) or Google (Gemini) implemented today |
| Tool layer | MCP server (official Python MCP SDK) |
| Embeddings + vectors | pgvector in Postgres |
| Frontend | Next.js |
| Deploy | Docker |
| GitHub integration | GitHub App (webhooks + fine-grained tokens) |

## Build order

1. GitHub App + webhook ingress
2. Queue + worker skeleton
3. MCP GitHub server
4. Retrieval layer (embeddings + pgvector)
5. Agent core (prompting + structured output + decision policy)
6. Guardrails + reliability (confidence gating, rate limits, retries)
7. Dashboard
8. Evaluation harness
9. Deploy
10. README + repo polish, demo, live end-to-end verification

## Local development

```bash
cp .env.example .env   # fill in GitHub App credentials, LLM API key
docker compose up -d   # starts Postgres (pgvector) + Redis
```

Individual services are documented in their own directories as they're
implemented.

## Running the full stack

```bash
cp .env.example .env   # fill in GITHUB_WEBHOOK_SECRET, GITHUB_TOKEN,
                        # LLM_PROVIDER + its API key, INTERNAL_API_TOKEN
docker compose up -d --build
```

Brings up all five containers: `postgres`, `redis`, `webhook-ingress`
(`:8000`), `worker`, and `dashboard` (`:3000`). `db/migrations/0001_init.sql`
applies automatically on a fresh `postgres` volume; anything after `0001`
needs applying by hand (see `db/README.md`) since it postdates the
container's first init.

Without an LLM API key/`GITHUB_TOKEN` set, the stack still runs - webhook
ingestion, queuing, retrieval/embedding, and the dashboard all work;
`worker` fails cleanly at the LLM call on any actual issue event until a
real key is set. mcp-server has no container of its own: `worker`
imports it in-process (see `worker/pipeline.py`) rather than spawning it
as a separate MCP server, so its code just ships inside the `worker`
image. `eval` isn't containerized either - it's a one-off CLI
(`python -m eval.main`), not an always-on service.

## License

MIT, see [`LICENSE`](LICENSE).
