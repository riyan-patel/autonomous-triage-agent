import { NextResponse } from "next/server";
import { getPool } from "../../../lib/db.js";
import { computeMetrics } from "../../../lib/metrics.js";

export async function GET() {
  const pool = getPool();
  const { rows } = await pool.query(
    "SELECT action_type, confidence FROM actions"
  );
  return NextResponse.json(computeMetrics(rows));
}
