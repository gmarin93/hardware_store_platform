// Session state for server components: always a cookie-bearing, no-store
// request to GET /auth/me. Never cached and never shared between users.
import type { ApiFailure, Me } from "@hardware-store/api-client";

import { sessionApi } from "./api/server";
import { settle } from "./result";

export type SessionState =
  | { kind: "anonymous" }
  /** Authenticated; `me.role` may be GUEST (signed in without permissions, ADR 0003). */
  | { kind: "signed-in"; me: Me }
  | { kind: "error"; failure: ApiFailure };

export function sessionFromResult(result: Awaited<ReturnType<typeof settle<Me>>>): SessionState {
  if (result.ok) return { kind: "signed-in", me: result.data };
  if (result.failure.status === 401) return { kind: "anonymous" };
  return { kind: "error", failure: result.failure };
}

export async function getSession(): Promise<SessionState> {
  const api = await sessionApi();
  return sessionFromResult(await settle(() => api.GET("/api/v1/auth/me")));
}
