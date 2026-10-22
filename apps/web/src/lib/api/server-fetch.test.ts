import { describe, expect, it, vi } from "vitest";

import { getApiInternalUrl } from "./config";
import { buildServerRequestInit, createServerFetch } from "./server-fetch";

function inboundLikeRequest(method = "GET") {
  // Simulates a request object carrying headers that must never be forwarded.
  return new Request("http://api:8000/api/v1/auth/me", {
    method,
    headers: {
      Cookie: "sessionid=abc; tracking=1",
      Host: "evil.example",
      "X-Forwarded-For": "203.0.113.9",
      "X-Forwarded-Host": "evil.example",
      "X-Forwarded-Proto": "https",
      Forwarded: "for=203.0.113.9",
      Authorization: "Bearer stolen",
      "X-CSRFToken": "tok",
      "User-Agent": "browser",
    },
  });
}

describe("server fetch adapter", () => {
  it("session mode sends only Accept and the allowlisted Cookie header, no-store", () => {
    const init = buildServerRequestInit(inboundLikeRequest(), {
      kind: "session",
      cookieHeader: "sessionid=abc; csrftoken=tok",
    });
    const headers = new Headers(init.headers);
    expect([...headers.keys()].sort()).toEqual(["accept", "cookie"]);
    expect(headers.get("cookie")).toBe("sessionid=abc; csrftoken=tok");
    expect(init.cache).toBe("no-store");
    expect(init.next).toBeUndefined();
    expect(init.redirect).toBe("manual");
  });

  it("session mode without allowlisted cookies sends no Cookie header", () => {
    const init = buildServerRequestInit(inboundLikeRequest(), { kind: "session", cookieHeader: null });
    expect([...new Headers(init.headers).keys()]).toEqual(["accept"]);
    expect(init.cache).toBe("no-store");
  });

  it("public mode never sends cookies and uses the revalidate window", () => {
    const init = buildServerRequestInit(inboundLikeRequest(), { kind: "public", revalidateSeconds: 60 });
    const headers = new Headers(init.headers);
    expect([...headers.keys()]).toEqual(["accept"]);
    expect(init.cache).toBeUndefined();
    expect(init.next).toEqual({ revalidate: 60 });
  });

  it("refuses unsafe methods so the server never logs in or out on a user's behalf", () => {
    for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
      expect(() => buildServerRequestInit(inboundLikeRequest(method), { kind: "session", cookieHeader: null })).toThrow(
        /read-only/,
      );
    }
  });

  it("passes the URL through and the rebuilt init to the base fetch", async () => {
    const baseFetch = vi.fn(async () => new Response("{}", { status: 200 }));
    const serverFetch = createServerFetch({ kind: "session", cookieHeader: "sessionid=abc" }, baseFetch);
    await serverFetch(inboundLikeRequest());
    expect(baseFetch).toHaveBeenCalledTimes(1);
    const [url, init] = baseFetch.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://api:8000/api/v1/auth/me");
    expect(new Headers(init.headers).get("x-forwarded-for")).toBeNull();
    expect(new Headers(init.headers).get("authorization")).toBeNull();
    expect(new Headers(init.headers).get("cookie")).toBe("sessionid=abc");
  });
});

describe("getApiInternalUrl", () => {
  it("returns the configured origin only", () => {
    expect(getApiInternalUrl({ API_INTERNAL_URL: "http://api:8000/" })).toBe("http://api:8000");
    expect(getApiInternalUrl({ API_INTERNAL_URL: "http://api:8000/some/path" })).toBe("http://api:8000");
  });

  it("fails closed when missing or not http(s)", () => {
    expect(() => getApiInternalUrl({})).toThrow();
    expect(() => getApiInternalUrl({ API_INTERNAL_URL: "file:///etc/passwd" })).toThrow();
  });
});
