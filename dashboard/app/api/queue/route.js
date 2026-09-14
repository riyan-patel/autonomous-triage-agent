import { NextResponse } from "next/server";
import { getPool } from "../../../lib/db.js";

// One row per issue's most recent triage decision, with any human review
// on it. DISTINCT ON keeps this to "the current state of each issue"
// rather than every historical decision - the full history is in
// `actions` directly for anyone who needs it.
const QUEUE_QUERY = `
  SELECT DISTINCT ON (i.repo_full_name, i.issue_number)
    i.repo_full_name,
    i.issue_number,
    i.title,
    i.state,
    a.id AS action_id,
    a.action_type,
    a.payload,
    a.confidence,
    a.dry_run,
    a.created_at AS decided_at,
    r.decision AS review_decision,
    r.reviewer AS reviewer
  FROM actions a
  JOIN issues i ON i.id = a.issue_id
  LEFT JOIN reviews r ON r.action_id = a.id
  ORDER BY i.repo_full_name, i.issue_number, a.created_at DESC
`;

export async function GET() {
  const pool = getPool();
  const { rows } = await pool.query(QUEUE_QUERY);
  rows.sort((a, b) => new Date(b.decided_at) - new Date(a.decided_at));
  return NextResponse.json({ items: rows });
}
