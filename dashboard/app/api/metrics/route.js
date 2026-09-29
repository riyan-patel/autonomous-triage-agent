import { NextResponse } from "next/server";
import { getPool } from "../../../lib/db.js";
import { computeMetrics } from "../../../lib/metrics.js";

export async function GET() {
  const pool = getPool();
  // Only the decision-making events ("act"/"escalate") count as an issue
  // being handled - "approved_execute" is a bookkeeping row recording that
  // an already-escalated issue's decision got carried out, not a new
  // triage decision, so it would otherwise double-count that issue here.
  const { rows } = await pool.query(
    "SELECT action_type, confidence FROM actions WHERE action_type IN ('act', 'escalate')"
  );
  return NextResponse.json(computeMetrics(rows));
}
