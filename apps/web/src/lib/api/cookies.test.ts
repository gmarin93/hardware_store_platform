import { describe, expect, it } from "vitest";

import { FORWARDED_COOKIE_NAMES, buildForwardedCookieHeader } from "./cookies";

describe("buildForwardedCookieHeader", () => {
  it("allowlists exactly sessionid and csrftoken", () => {
    expect([...FORWARDED_COOKIE_NAMES]).toEqual(["sessionid", "csrftoken"]);
  });

  it("forwards only the session and CSRF cookies, in a stable order", () => {
    const header = buildForwardedCookieHeader([
      { name: "csrftoken", value: "Tok3n" },
      { name: "analytics", value: "track-me" },
      { name: "sessionid", value: "abc123" },
      { name: "next-auth.session-token", value: "other" },
      { name: "SESSIONID", value: "case-variant" },
    ]);
    expect(header).toBe("sessionid=abc123; csrftoken=Tok3n");
  });

  it("returns null when no allowlisted cookie is present", () => {
    expect(buildForwardedCookieHeader([])).toBeNull();
    expect(buildForwardedCookieHeader([{ name: "theme", value: "dark" }])).toBeNull();
  });

  it("drops values that could smuggle extra cookies or headers", () => {
    const header = buildForwardedCookieHeader([
      { name: "sessionid", value: "abc; admin=1" },
      { name: "csrftoken", value: "tok\r\nX-Forwarded-For: 1.2.3.4" },
    ]);
    expect(header).toBeNull();
    expect(buildForwardedCookieHeader([{ name: "sessionid", value: "" }])).toBeNull();
    expect(buildForwardedCookieHeader([{ name: "sessionid", value: "a b" }])).toBeNull();
  });

  it("keeps the first occurrence of a duplicated cookie", () => {
    expect(
      buildForwardedCookieHeader([
        { name: "sessionid", value: "first" },
        { name: "sessionid", value: "second" },
      ]),
    ).toBe("sessionid=first");
  });
});
