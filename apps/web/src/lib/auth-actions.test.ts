import { createApiClient } from "@hardware-store/api-client";
import { describe, expect, it, vi } from "vitest";

import { readCsrfToken } from "./api/browser";
import { login, logout } from "./auth-actions";

const meBody = {
  user: { id: "00000000-0000-4000-8000-000000000002", email: "cliente.demo@example.test", full_name: "Cliente" },
  organization: null,
  role: "CUSTOMER",
  branches: [],
  permissions: [],
};

function harness(responses: Record<string, () => Response>) {
  const calls: Request[] = [];
  const fetchMock = vi.fn(async (request: Request) => {
    calls.push(request);
    const key = `${request.method} ${new URL(request.url).pathname}`;
    const make = responses[key];
    if (!make) throw new Error(`unexpected ${key}`);
    return make();
  });
  const api = createApiClient({ baseUrl: "http://web.test", fetch: fetchMock });
  return { api, calls };
}

const json = (body: unknown, status: number) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("readCsrfToken", () => {
  it("reads the csrftoken cookie only", () => {
    expect(readCsrfToken("theme=dark; csrftoken=abc123; other=x")).toBe("abc123");
    expect(readCsrfToken("xcsrftoken=nope")).toBeNull();
    expect(readCsrfToken("")).toBeNull();
  });
});

describe("login", () => {
  it("fetches the CSRF cookie first and sends it as X-CSRFToken", async () => {
    const { api, calls } = harness({
      "GET /api/v1/auth/csrf": () => new Response(null, { status: 204 }),
      "POST /api/v1/auth/login": () => json(meBody, 200),
    });
    const result = await login({ api, readCookies: () => "csrftoken=fresh-token" }, "cliente.demo@example.test", "secret");
    expect(result.ok).toBe(true);
    expect(calls.map((request) => `${request.method} ${new URL(request.url).pathname}`)).toEqual([
      "GET /api/v1/auth/csrf",
      "POST /api/v1/auth/login",
    ]);
    const post = calls[1]!;
    expect(post.headers.get("x-csrftoken")).toBe("fresh-token");
    expect(await post.json()).toEqual({ email: "cliente.demo@example.test", password: "secret" });
  });

  it("returns the es-CR envelope for invalid credentials", async () => {
    const envelope = {
      code: "INVALID_CREDENTIALS",
      message: "Correo o contraseña incorrectos.",
      field_errors: {},
      request_id: "req-9",
    };
    const { api } = harness({
      "GET /api/v1/auth/csrf": () => new Response(null, { status: 204 }),
      "POST /api/v1/auth/login": () => json(envelope, 400),
    });
    const result = await login({ api, readCookies: () => "csrftoken=t" }, "x@example.test", "wrong");
    expect(result).toEqual({ ok: false, failure: { status: 400, envelope, fromServer: true } });
  });

  it("reports network failures without throwing", async () => {
    const api = createApiClient({
      baseUrl: "http://web.test",
      fetch: async () => {
        throw new TypeError("fetch failed");
      },
    });
    const result = await login({ api, readCookies: () => "" }, "x@example.test", "pw");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.failure.envelope.code).toBe("NETWORK_ERROR");
  });
});

describe("logout", () => {
  it("posts with the CSRF header and accepts 204", async () => {
    const { api, calls } = harness({
      "GET /api/v1/auth/csrf": () => new Response(null, { status: 204 }),
      "POST /api/v1/auth/logout": () => new Response(null, { status: 204 }),
    });
    const result = await logout({ api, readCookies: () => "csrftoken=tok" });
    expect(result).toEqual({ ok: true, data: null });
    expect(calls[1]?.headers.get("x-csrftoken")).toBe("tok");
  });

  it("returns CSRF_FAILED envelopes", async () => {
    const envelope = { code: "CSRF_FAILED", message: "Falló la verificación CSRF.", field_errors: {}, request_id: "r" };
    const { api } = harness({
      "GET /api/v1/auth/csrf": () => new Response(null, { status: 204 }),
      "POST /api/v1/auth/logout": () => json(envelope, 403),
    });
    const result = await logout({ api, readCookies: () => "" });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.failure.envelope.code).toBe("CSRF_FAILED");
  });
});
