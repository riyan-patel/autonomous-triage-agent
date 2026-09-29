import { NextResponse } from "next/server";
import { getPool } from "../../../lib/db.js";

const VALID_DECISIONS = new Set(["approved", "rejected"]);

// webhook-ingress owns the Redis/RQ connection (Python's `rq` library uses
// a pickle-based wire format the dashboard, being Node, can't produce
// directly) - so triggering real execution means an HTTP call to its
// internal endpoint rather than enqueueing a job ourselves. See
// webhook-ingress/app/main.py:execute_approval.
const WEBHOOK_INGRESS_URL = process.env.WEBHOOK_INGRESS_URL || "http://localhost:8000";
const INTERNAL_API_TOKEN = process.env.INTERNAL_API_TOKEN || "";

async function triggerExecution(actionId) {
  const response = await fetch(
    `${WEBHOOK_INGRESS_URL}/internal/approvals/${actionId}/execute`,
    {
      method: "POST",
      headers: { "X-Internal-Token": INTERNAL_API_TOKEN },
    }
  );
  if (!response.ok) {
    throw new Error(`webhook-ingress returned ${response.status}`);
  }
}

// Records a human decision on an escalated action (suggest mode), then -
// for an "approved" decision - triggers the worker to actually execute it
// against GitHub via mcp-server's tools. A "rejected" decision is recorded
// and nothing further happens. Execution failure doesn't fail the review
// write itself (the decision is real either way); it's surfaced back in
// the response so the UI can show it instead of silently dropping it.
export async function POST(request) {
  const body = await request.json();
  const { action_id: actionId, decision, reviewer } = body ?? {};

  if (!Number.isInteger(actionId)) {
    return NextResponse.json({ error: "action_id must be an integer" }, { status: 400 });
  }
  if (!VALID_DECISIONS.has(decision)) {
    return NextResponse.json(
      { error: `decision must be one of: ${[...VALID_DECISIONS].join(", ")}` },
      { status: 400 }
    );
  }

  const pool = getPool();
  let review;
  try {
    const { rows } = await pool.query(
      `INSERT INTO reviews (action_id, decision, reviewer)
       VALUES ($1, $2, $3)
       ON CONFLICT (action_id) DO UPDATE SET decision = EXCLUDED.decision, reviewer = EXCLUDED.reviewer
       RETURNING id, action_id, decision, reviewer, created_at`,
      [actionId, decision, reviewer ?? null]
    );
    review = rows[0];
  } catch (err) {
    if (err.code === "23503") {
      // foreign key violation: action_id references actions(id)
      return NextResponse.json({ error: "no action with that id" }, { status: 404 });
    }
    throw err;
  }

  if (decision !== "approved") {
    return NextResponse.json({ review }, { status: 201 });
  }

  try {
    await triggerExecution(actionId);
    return NextResponse.json({ review, execution: "triggered" }, { status: 201 });
  } catch (err) {
    return NextResponse.json(
      { review, execution: "trigger_failed", execution_error: err.message },
      { status: 201 }
    );
  }
}
