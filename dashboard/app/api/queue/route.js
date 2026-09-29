import { NextResponse } from "next/server";
import { getPool } from "../../../lib/db.js";

// One row per issue's most recent *decision* ("act"/"escalate"), with any
// human review and execution status attached. Deliberately keyed off the
// most recent decision row rather than the most recent action row overall:
// "approved_execute" is a bookkeeping row recording that an escalated
// decision got carried out, and reviews.action_id always references the
// original "escalate" row - if we picked the latest action row overall,
// an executed issue's review/decision would stop matching the moment its
// approved_execute row became newer than its escalate row.
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
    r.reviewer AS reviewer,
    (ex.id IS NOT NULL) AS executed
  FROM actions a
  JOIN issues i ON i.id = a.issue_id
  LEFT JOIN reviews r ON r.action_id = a.id
  LEFT JOIN actions ex ON ex.issue_id = a.issue_id AND ex.action_type = 'approved_execute'
  WHERE a.action_type IN ('act', 'escalate')
  ORDER BY i.repo_full_name, i.issue_number, a.created_at DESC
`;

export async function GET() {
  const pool = getPool();
  const { rows } = await pool.query(QUEUE_QUERY);
  rows.sort((a, b) => new Date(b.decided_at) - new Date(a.decided_at));
  return NextResponse.json({ items: rows });
}
