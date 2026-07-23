# mcp-server

MCP server exposing GitHub actions as standardized tools that the agent
core calls as an MCP client:

- `apply_labels(issue, labels[])`
- `post_comment(issue, body)`
- `assign_reviewer(issue, user)`
- `link_duplicate(issue, other)`
- `search_issues(query)`

Not yet implemented — see build order step 3 in `docs/ARCHITECTURE.md`.
