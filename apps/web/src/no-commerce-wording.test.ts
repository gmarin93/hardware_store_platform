// P1 has no price, availability, stock, cart, checkout or payment UI (ADR 0001,
// CLAUDE.md). Guards user-facing source files against such wording.
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const SRC = path.dirname(new URL(import.meta.url).pathname);
const FORBIDDEN =
  /\b(precios?|disponib\w*|existencias?|inventario|stock|carrito|checkout|pagos?|pagar|tarjeta|comprar|price|cart|payment)\b/i;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return name === "integration" ? [] : sourceFiles(full);
    return /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) ? [full] : [];
  });
}

describe("no commerce wording in the UI", () => {
  it("source files contain no price/availability/cart/payment wording", () => {
    const offenders = sourceFiles(SRC).flatMap((file) =>
      readFileSync(file, "utf8")
        .split("\n")
        .map((line, index) => ({ file: path.relative(SRC, file), line: index + 1, text: line }))
        .filter(({ text }) => FORBIDDEN.test(text)),
    );
    expect(offenders).toEqual([]);
  });
});
