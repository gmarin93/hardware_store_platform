// Regenerates src/generated/openapi.d.ts from contracts/openapi.yaml with the
// pinned openapi-typescript CLI. `--check` regenerates into a temporary file
// and fails (exit 1) when the committed output differs. No network access:
// the contract is a local file.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const packageDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const contract = path.resolve(packageDir, "../../contracts/openapi.yaml");
const committed = path.join(packageDir, "src/generated/openapi.d.ts");
const cli = path.resolve(packageDir, "../../node_modules/openapi-typescript/bin/cli.js");

function generate(output) {
  execFileSync(process.execPath, [cli, contract, "--output", output], {
    cwd: packageDir,
    stdio: ["ignore", "ignore", "inherit"],
  });
}

if (process.argv.includes("--check")) {
  const dir = mkdtempSync(path.join(tmpdir(), "api-client-"));
  try {
    const fresh = path.join(dir, "openapi.d.ts");
    generate(fresh);
    if (readFileSync(fresh, "utf8") !== readFileSync(committed, "utf8")) {
      console.error(
        "api-client: src/generated/openapi.d.ts is out of date with contracts/openapi.yaml. " +
          "Run `npm run api-client:generate` and commit the result.",
      );
      process.exit(1);
    }
    console.log("api-client: generated types match contracts/openapi.yaml");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
} else {
  generate(committed);
  console.log("api-client: wrote src/generated/openapi.d.ts");
}
