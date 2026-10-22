import path from "node:path";
import type { NextConfig } from "next";

// Monorepo root (npm workspaces). Used for Turbopack resolution and for
// standalone output tracing so the Docker image includes hoisted packages.
const monorepoRoot = path.join(__dirname, "../..");

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: monorepoRoot,
  turbopack: { root: monorepoRoot },
  // Workspace package shipped as TypeScript source (packages/api-client).
  transpilePackages: ["@hardware-store/api-client"],
  poweredByHeader: false,
  reactStrictMode: true,
};

export default nextConfig;
