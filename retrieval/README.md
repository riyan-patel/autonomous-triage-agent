# retrieval

Embedding + indexing pipeline. Backfills existing issues into pgvector,
embeds new issues at triage time, and runs k-NN cosine search for
duplicate detection and RAG context. Also handles reviewer routing via
CODEOWNERS + recent commit authors.

Not yet implemented — see build order step 4 in `docs/ARCHITECTURE.md`.
