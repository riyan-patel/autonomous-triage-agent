# dashboard

Next.js dashboard: live triage queue, per-issue detail (summary, labels,
duplicate link, draft reply, confidence), Approve/Reject actions for
suggest mode, and a metrics panel.

## Status

Implemented:

- `app/page.js` — the triage queue: a metrics row (issues handled, acted
  vs. escalated, escalation rate, avg confidence) and a table of every
  issue's most recent triage decision, with Approve/Reject buttons on
  escalated items that haven't been reviewed yet.
- `app/api/queue/route.js` — `GET`, one row per issue's latest `actions`
  row (`DISTINCT ON`), left-joined with any `reviews` row on it.
- `app/api/metrics/route.js` — `GET`, aggregates over `actions` via the
  pure `lib/metrics.js` (unit-tested with Vitest, no DB needed).
- `app/api/reviews/route.js` — `POST {action_id, decision}`, upserts a row
  into `reviews` (`decision` is `approved`/`rejected`).

Talks directly to Postgres (`lib/db.js`, via `pg`) rather than through a
Python API service — the tables it reads (`issues`, `actions`) are the
ones `worker`'s audit log (build order step 6) already writes to, so the
dashboard is a live view of real triage activity with no extra service to
run.

Not yet implemented: **approving an action only records the decision** —
it doesn't call mcp-server's tools to actually execute it against GitHub
yet. That needs a worker-side consumer of the `reviews` table (poll for
unapplied approvals, call `apply_labels`/`post_comment`/etc.), which is a
separate task from the dashboard itself. Also not yet done: auth (this is
an internal tool with no login), and duplicate-issue linking in the UI
(the data - `payload.duplicate_of` - is already in the API response).

Migration `db/migrations/0002_add_reviews.sql` adds the `reviews` table;
apply it by hand against an existing Postgres volume (see `db/README.md`)
since it postdates `0001`.

### Known dev-dependency vulnerabilities

`npm audit` flags moderate/high issues in `vitest`'s bundled `esbuild`/
`vite` and in `next`'s bundled `postcss` - all dev-server/build-time only,
fixed by major version bumps (`next@16`, `vitest@5`) intentionally not
taken here to avoid unrelated breakage this early. Revisit before any
production deploy (build order step 9).

## Local development

```bash
cd dashboard
npm install

npm test        # vitest, pure logic only, no DB needed

# needs Postgres up with 0001 + 0002 applied
export DATABASE_URL=postgresql://triage:triage@localhost:5432/triage_agent
npm run dev      # http://localhost:3000
```
