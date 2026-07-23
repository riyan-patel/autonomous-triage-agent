# agent-core

The reasoning loop: builds the prompt (issue + retrieved context + label
taxonomy + few-shot examples), calls the LLM for schema-constrained
structured output, and applies the confidence-gated decision policy
(act vs. escalate).

Not yet implemented — see build order step 5 in `docs/ARCHITECTURE.md`.
