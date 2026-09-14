import { NextResponse } from "next/server";
import { getPool } from "../../../lib/db.js";

const VALID_DECISIONS = new Set(["approved", "rejected"]);

// Records a human decision on an escalated action (suggest mode). This
// only records the decision - it does not execute it against GitHub yet.
// Approving an action still requires a follow-up worker-side consumer of
// this table to actually call mcp-server's tools; wiring that up is a
// separate task from the dashboard itself.
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
  try {
    const { rows } = await pool.query(
      `INSERT INTO reviews (action_id, decision, reviewer)
       VALUES ($1, $2, $3)
       ON CONFLICT (action_id) DO UPDATE SET decision = EXCLUDED.decision, reviewer = EXCLUDED.reviewer
       RETURNING id, action_id, decision, reviewer, created_at`,
      [actionId, decision, reviewer ?? null]
    );
    return NextResponse.json({ review: rows[0] }, { status: 201 });
  } catch (err) {
    if (err.code === "23503") {
      // foreign key violation: action_id references actions(id)
      return NextResponse.json({ error: "no action with that id" }, { status: 404 });
    }
    throw err;
  }
}
