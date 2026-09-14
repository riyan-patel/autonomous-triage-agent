import { Pool } from "pg";

let pool;

// One pool per server process (Next.js dev-mode module reload can create
// duplicates otherwise - stash it on globalThis so a hot reload reuses it).
export function getPool() {
  if (!globalThis.__triagePgPool) {
    globalThis.__triagePgPool = new Pool({
      connectionString:
        process.env.DATABASE_URL ||
        "postgresql://triage:triage@localhost:5432/triage_agent",
    });
  }
  pool = globalThis.__triagePgPool;
  return pool;
}
