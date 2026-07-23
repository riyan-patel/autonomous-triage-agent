# Autonomous GitHub Triage Agent

An always-on, autonomous AI agent that takes GitHub issue triage off a
maintainer's plate. The moment a new issue is filed, it reads it,
summarizes it, labels it, detects duplicates, suggests a reviewer, and
drafts a first response — through a standardized MCP tool layer, with a
web dashboard and a measured accuracy number.

> **Status: scaffolding.** This repo currently holds the architecture and
> project skeleton. Components are being implemented in the build order
> below.

## Why this exists

The LLM here is a commodity component that gets called — the actual
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
          │  Dashboard   │  (Next.js — live queue, actions, metrics)
          └──────────────┘
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full technical
plan: component depth, reliability/safety engineering, and the evaluation
methodology.

## Repo layout

| Path | Purpose |
|---|---|
| `webhook-ingress/` | FastAPI service: receives + HMAC-verifies GitHub webhooks, enqueues jobs |
| `worker/` | Queue worker: pulls jobs, drives the agent core, handles retries/idempotency |
| `mcp-server/` | MCP server exposing GitHub actions as standardized tools (`apply_labels`, `post_comment`, `assign_reviewer`, `link_duplicate`, `search_issues`) |
| `retrieval/` | Embedding + indexing pipeline, pgvector k-NN search for duplicates and reviewer routing |
| `agent-core/` | The reasoning loop: prompt construction, structured output, confidence-gated decision policy |
| `dashboard/` | Next.js dashboard: live triage queue, audit log, approve/reject UI, metrics |
| `eval/` | Evaluation harness: labeled benchmark + accuracy/precision/recall metrics |
| `db/` | Postgres schema + migrations |
| `scripts/` | One-off / operational scripts (backfill, seed data, etc.) |
| `docs/` | Architecture doc and design notes |

## Tech stack

| Layer | Choice |
|---|---|
| Backend / agent | Python, FastAPI |
| Queue | Redis + RQ |
| LLM | Swappable via API (Claude / GPT / Gemini) |
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
10. README + repo polish, demo

## Local development

```bash
cp .env.example .env   # fill in GitHub App credentials, LLM API key
docker compose up -d   # starts Postgres (pgvector) + Redis
```

Individual services are documented in their own directories as they're
implemented.

## License

MIT — see [`LICENSE`](LICENSE).
