# agent-core

The reasoning loop: builds the prompt (issue + retrieved context + label
taxonomy + few-shot examples), calls the LLM for schema-constrained
structured output, and applies the confidence-gated decision policy
(act vs. escalate).

## Status

Implemented:

- `schema.py` — `TriageOutput`: the structured contract the LLM must
  produce (`summary`, `type`, `severity`, `labels`, `duplicate_of`,
  `suggested_reviewer`, `draft_reply`, `confidence`).
- `prompt.py` — builds the system + user prompt from an issue, the repo's
  label taxonomy, retrieved similar issues (from `retrieval/`), and
  optional few-shot examples.
- `llm.py` — `LLMClient` interface; `AnthropicLLMClient` forces structured
  output via tool use (the model must call a single tool shaped like
  `TriageOutput.model_json_schema()`), so the result is always parseable.
- `policy.py` — confidence-gated decision: below `confidence_threshold`
  always escalates; a `duplicate_of` link additionally needs threshold+0.1
  margin, since a wrong duplicate link is more disruptive to undo than a
  wrong label.
- `pipeline.py` — `run_triage(...)` wires prompt → LLM → policy. Retrieval
  and acting on the decision (MCP tool calls) stay the caller's
  responsibility, so this stays testable with a fake LLM client.

Not yet implemented: wiring this into `worker/pipeline.py` (replacing its
`not_implemented` stub) so a real webhook actually reaches this code, and
calling `mcp-server`'s tools when the decision is `act`. That's the
natural next step once this is reviewed.

Not live-tested against the real Anthropic API in this environment (no
`ANTHROPIC_API_KEY` configured) — `AnthropicLLMClient` is covered by tests
that mock the SDK's response shape (`tests/test_llm.py`), matching how the
real `messages.create(..., tools=[...], tool_choice=...)` call and
tool-use response are structured.

## Local development

```bash
cd agent-core
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

pytest
```

To exercise `AnthropicLLMClient` for real, set `ANTHROPIC_API_KEY` and
`LLM_MODEL`, then call `run_triage` with an `AnthropicLLMClient` instance
instead of a fake.
