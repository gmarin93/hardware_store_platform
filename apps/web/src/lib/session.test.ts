import type { Me } from "@hardware-store/api-client";
import { toApiFailure } from "@hardware-store/api-client";
import { describe, expect, it } from "vitest";

import { sessionFromResult } from "./session";

const guestMe: Me = {
  user: { id: "00000000-0000-4000-8000-000000000001", email: "sin.rol@example.test", full_name: "Sin Rol" },
  organization: null,
  role: "GUEST",
  branches: [],
  permissions: ["catalog.view_published"],
};

describe("sessionFromResult", () => {
  it("treats an authenticated GUEST as signed in, not anonymous", () => {
    expect(sessionFromResult({ ok: true, data: guestMe })).toEqual({ kind: "signed-in", me: guestMe });
  });

  it("treats 401 as anonymous", () => {
    const failure = toApiFailure(401, {
      code: "NOT_AUTHENTICATED",
      message: "Debe iniciar sesión.",
      field_errors: {},
      request_id: "r",
    });
    expect(sessionFromResult({ ok: false, failure })).toEqual({ kind: "anonymous" });
  });

  it("surfaces other failures as errors", () => {
    const failure = toApiFailure(0, undefined);
    expect(sessionFromResult({ ok: false, failure }).kind).toBe("error");
  });
});
