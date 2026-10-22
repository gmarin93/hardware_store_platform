import { createApiClient, fieldMessages, isErrorEnvelope, toApiFailure } from "@hardware-store/api-client";
import { describe, expect, it } from "vitest";

import { settle } from "./result";

const envelope = {
  code: "INVALID_CURSOR",
  message: "El cursor de paginación no es válido.",
  field_errors: {},
  request_id: "req-1",
};

function clientReturning(response: Response | Error) {
  return createApiClient({
    baseUrl: "http://api.test",
    fetch: async () => {
      if (response instanceof Error) throw response;
      return response;
    },
  });
}

describe("error envelope helpers", () => {
  it("recognizes only well-formed envelopes", () => {
    expect(isErrorEnvelope(envelope)).toBe(true);
    expect(isErrorEnvelope({ ...envelope, field_errors: { email: [{ code: "x", message: "y" }] } })).toBe(true);
    expect(isErrorEnvelope({ detail: "Not found." })).toBe(false);
    expect(isErrorEnvelope("<html>Bad gateway</html>")).toBe(false);
    expect(isErrorEnvelope({ ...envelope, field_errors: { email: "bad" } })).toBe(false);
  });

  it("synthesizes a Spanish fallback for non-envelope bodies", () => {
    const failure = toApiFailure(502, "<html>Bad gateway</html>");
    expect(failure.fromServer).toBe(false);
    expect(failure.envelope.code).toBe("UNEXPECTED_RESPONSE");
    expect(failure.envelope.message).toMatch(/inesperada/);
  });

  it("returns field messages by path", () => {
    const withFields = { ...envelope, field_errors: { email: [{ code: "invalid", message: "Correo inválido." }] } };
    expect(fieldMessages(withFields, "email")).toEqual(["Correo inválido."]);
    expect(fieldMessages(withFields, "password")).toEqual([]);
  });
});

describe("settle", () => {
  it("returns data on success", async () => {
    const api = clientReturning(
      new Response(JSON.stringify({ results: [], next_cursor: null, previous_cursor: null }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const result = await settle(() => api.GET("/api/v1/catalog/products"));
    expect(result).toEqual({ ok: true, data: { results: [], next_cursor: null, previous_cursor: null } });
  });

  it("keeps the server envelope and status on API errors", async () => {
    const api = clientReturning(
      new Response(JSON.stringify(envelope), { status: 400, headers: { "Content-Type": "application/json" } }),
    );
    const result = await settle(() => api.GET("/api/v1/catalog/products"));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.status).toBe(400);
      expect(result.failure.envelope).toEqual(envelope);
      expect(result.failure.fromServer).toBe(true);
    }
  });

  it("maps thrown network errors to NETWORK_ERROR (status 0)", async () => {
    const api = clientReturning(new TypeError("fetch failed"));
    const result = await settle(() => api.GET("/api/v1/catalog/products"));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.status).toBe(0);
      expect(result.failure.envelope.code).toBe("NETWORK_ERROR");
    }
  });
});
