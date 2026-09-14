import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Silences a workspace-root inference warning: there's an unrelated
  // package-lock.json in the user's home directory that Next.js would
  // otherwise mistake for a monorepo root above this project.
  outputFileTracingRoot: __dirname,
  // Produces .next/standalone: a minimal server bundle with only the
  // node_modules it actually needs, so the Docker image doesn't have to
  // ship the full node_modules tree.
  output: "standalone",
};

export default nextConfig;
