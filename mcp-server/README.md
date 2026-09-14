# mcp-server

MCP server exposing GitHub actions as standardized tools that the agent
core calls as an MCP client:

- `apply_labels(repo, issue_number, labels[])`
- `post_comment(repo, issue_number, body)`
- `assign_reviewer(repo, issue_number, username)`
- `link_duplicate(repo, issue_number, duplicate_of)`
- `search_issues(repo, query, limit=10)`

## Status

Implemented: all five tools, backed by `GitHubClient` (a thin PyGithub
wrapper). Guardrails from `docs/ARCHITECTURE.md` are in place at this
layer:

- **Allow-listed actions only** — these five methods are the entire
  surface; there's no way to close an issue or push code through this
  server.
- **Dry-run mode** (`DRY_RUN=true`, the default) — every mutating call
  logs what it *would* do and returns without touching GitHub.
- **No-spam idempotency** — `post_comment` and `link_duplicate` check for
  the agent's own marker (`AGENT_COMMENT_MARKER`) in existing comments and
  skip posting a second time on the same issue.

Not yet implemented: GitHub App installation-token auth. `GITHUB_TOKEN`
(a personal access token) is the local-dev auth path for now; wiring the
GitHub App private key → short-lived installation token exchange is
deferred until the server is actually deployed against a real
installation.

## Local development

```bash
cd mcp-server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# run the test suite (fakes stand in for PyGithub, no GitHub API calls)
pytest

# run the server over stdio (safe by default: DRY_RUN=true)
python -m mcp_server.main
```

To act on a real repo, set `GITHUB_TOKEN` (a PAT with `repo` scope) and
`DRY_RUN=false` before running. Leave `DRY_RUN=true` for anything you
haven't verified end-to-end yet.
