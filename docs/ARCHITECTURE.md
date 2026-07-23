# Autonomous GitHub Triage Agent — Technical Plan

## 1. Functional spec

On every new/updated issue, the agent autonomously:

1. **Summarizes** the issue in one line.
2. **Classifies** it: bug / feature / question / docs, plus severity.
3. **Labels** it using the repo's actual label taxonomy.
4. **Detects duplicates** by semantic similarity against existing issues,
   linking the most likely match.
5. **Suggests a reviewer/owner** based on which files/areas the issue
   relates to (via code ownership / recent authors).
6. **Drafts a first-response comment** (asks for a repro, points to docs,
   or acknowledges).
7. **Decides autonomously** whether to act (apply labels/comment) or
   escalate to a human when confidence is low.
8. Logs every action to a dashboard with an audit trail.

Two operating modes: **suggest mode** (drafts everything, human approves)
and **autonomous mode** (acts directly on high-confidence items, escalates
the rest). Confidence-gated autonomy is the core design decision.

## 2. Concepts and where they live

| Concept | Where it's used |
|---|---|
| Agentic AI / autonomous agent | Core control loop: perceive event → reason → act via tools, no human in the loop |
| Tool use / function calling | LLM emits structured tool calls (`apply_labels`, `post_comment`, `assign`, `link_duplicate`) that code executes |
| MCP (Model Context Protocol) | MCP server exposing GitHub actions as standardized tools; the agent is the MCP client |
| RAG | Agent retrieves relevant existing issues + repo docs + label descriptions before deciding |
| Semantic search / embeddings + vector DB | Duplicate detection and reviewer routing via cosine similarity |
| Autonomous decision-making / routing | Confidence-gated policy: act vs. escalate; reviewer choice; label set |
| Structured output | JSON schema-constrained generation for machine-actionable, safe outputs |
| Prompt engineering | System prompts, few-shot exemplars from the repo's own past triage |
| Guardrails / safety | Rate limits, no-spam rules, idempotency, human-approval gate, allow-listed actions |
| Evaluation | Labeled test set + metrics (label accuracy, duplicate precision/recall) |

## 3. System architecture

```
        GitHub repo
            │  (webhook: issues.opened / edited)
            ▼
   ┌─────────────────┐     enqueue     ┌──────────────┐
   │  Webhook Ingress │ ──────────────▶ │  Job Queue    │  (Redis / RQ or Celery)
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

### A. Webhook ingress (FastAPI)

GitHub sends a signed webhook on `issues.opened`/`edited`. Verify the
HMAC-SHA256 signature (`X-Hub-Signature-256`) to reject forgeries, then
immediately enqueue and return `200` fast (GitHub times out webhooks at
~10s). *Concepts: event-driven architecture, webhook security, fast-ack.*

### B. Job queue + workers (Redis + RQ/Celery)

Decouples ingestion from processing. Provides retries with backoff,
concurrency control, and idempotency (dedupe by `delivery_id` so GitHub
re-deliveries don't double-act). *Concepts: async processing, at-least-once
delivery, idempotency keys.*

### C. Retrieval layer

- **Indexing:** on install, backfill all open issues → embed title+body →
  store vectors in pgvector (inside Postgres — one datastore).
- **At triage time:** embed the new issue, run k-NN cosine search for the
  top-N most similar existing issues → duplicate candidates *and* RAG
  context.
- **Reviewer routing:** map issue → likely files/areas (keywords +
  `CODEOWNERS` + recent commit authors) to suggest an owner.

*Concepts: embeddings, semantic search, vector databases, k-NN, RAG
grounding.*

### D. Agent core (reasoning loop)

- Build the prompt: issue text + retrieved duplicates + repo's label
  taxonomy (with descriptions) + few-shot examples from the repo's own
  historically-labeled issues.
- Call the LLM with schema-constrained structured output: `{summary, type,
  severity, labels[], duplicate_of, suggested_reviewer, draft_reply,
  confidence}`.
- Apply the decision policy: if `confidence ≥ threshold` and action is
  non-destructive → act; else → escalate (leave a draft for human
  approval).

*Concepts: agentic loop, tool use, structured generation, autonomous
decision policy.*

### E. MCP GitHub server

Actions exposed as MCP tools: `apply_labels(issue, labels[])`,
`post_comment(issue, body)`, `assign_reviewer(issue, user)`,
`link_duplicate(issue, other)`, `search_issues(query)`. The agent core is
the MCP client that calls them — this keeps the tool layer standardized,
testable, and separable from the reasoning logic.

### F. Persistence (Postgres + pgvector)

Tables: `issues`, `actions` (full audit log of every decision + reasoning
+ confidence), `eval_labels` (ground truth for evaluation),
`installations`. The audit log doubles as the evaluation data source.

### G. Dashboard (Next.js)

Live triage queue, each item showing the agent's summary, chosen labels,
duplicate link, draft reply, confidence, and Approve/Reject buttons
(suggest mode). Metrics panel: issues handled, avg time-to-first-response,
label accuracy.

## 4. Reliability & safety engineering

- **Idempotency:** every GitHub delivery has an ID; store processed IDs so
  re-deliveries are no-ops.
- **Rate limiting:** token-bucket throttling + respect `Retry-After`; back
  off on `403/429`.
- **Retries & dead-letter:** transient failures retry with exponential
  backoff; permanent failures go to a dead-letter queue for inspection.
- **Confidence gating:** low-confidence issues never auto-act — they
  escalate. Tunable threshold.
- **Guardrails:** allow-listed actions only (agent cannot close issues or
  push code); no-spam caps (max 1 comment/issue); a dry-run mode.
- **Secrets:** GitHub App private key + tokens in a secrets manager, never
  in code.
- **Observability:** structured logging + metrics on actions, latencies,
  escalation rate.

## 5. Evaluation

A labeled benchmark of ~100–200 already-triaged issues from a real repo
(their true labels are ground truth). Measure:

- **Label accuracy / F1** (predicted vs. actual labels).
- **Duplicate detection precision & recall** (against known duplicate
  links).
- **Escalation calibration** (precision at high confidence — of the
  auto-acted items, how many were correct).

## 6. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python (agent/backend) + TypeScript (dashboard) | AI stack + UI stack |
| API / webhooks | FastAPI | Async, fast, clean webhook handling |
| Queue | Redis + RQ (or Celery) | Simple, reliable async workers, retries |
| LLM | Any strong API model | Commodity reasoning component — swappable |
| Tool layer | MCP server (official Python MCP SDK) | Standardized, testable |
| Embeddings + vectors | pgvector in Postgres | One datastore for data + vectors |
| Structured output | JSON schema / function-calling | Machine-actionable, safe outputs |
| Frontend | Next.js | React/Next stack |
| Deploy | Docker on cloud host | Real deployment |
| GitHub integration | GitHub App (webhooks + fine-grained tokens) | The legit way; installable on real repos |

## 7. Build order

1. GitHub App + webhook ingress — receive and verify events, log them.
2. Queue + worker skeleton — enqueue events, process async, idempotency.
3. MCP GitHub server — implement action tools; test standalone.
4. Retrieval layer — backfill + embed issues into pgvector; k-NN search.
5. Agent core — prompt + structured output + decision policy; wire to MCP.
6. Guardrails + reliability — confidence gating, rate limits, retries, dry-run.
7. Dashboard — live queue, actions, approve/reject.
8. Evaluation harness — labeled set + metrics.
9. Deploy — Dockerize, ship to a host, install on a public repo, demo.
10. README + repo polish — architecture diagram, the metric, a demo GIF.

Ship a thin end-to-end slice early (steps 1–5 doing *one* action) before
adding breadth.
