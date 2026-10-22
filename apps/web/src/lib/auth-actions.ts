// Browser-side session actions. The browser itself talks to Django through the
// same-origin proxy, so session cookies are set only on the user's own
// response; the Next.js server never logs in on a user's behalf.
import { networkFailure, toApiFailure, type ApiClient, type ApiFailure, type Me } from "@hardware-store/api-client";

import { readCsrfToken } from "./api/browser";

export const SESSION_CHANGED_EVENT = "hwp:session-changed";

export interface SessionDeps {
  api: ApiClient;
  /** Returns the current `document.cookie` string. */
  readCookies: () => string;
}

export type ActionResult<T> = { ok: true; data: T } | { ok: false; failure: ApiFailure };

async function ensureCsrfToken(deps: SessionDeps): Promise<string | null> {
  // Always refresh: login rotates the token (ADR 0003).
  const { response } = await deps.api.GET("/api/v1/auth/csrf");
  if (!response.ok) return null;
  return readCsrfToken(deps.readCookies());
}

export async function login(deps: SessionDeps, email: string, password: string): Promise<ActionResult<Me>> {
  try {
    const token = await ensureCsrfToken(deps);
    const { data, error, response } = await deps.api.POST("/api/v1/auth/login", {
      body: { email, password },
      headers: token ? { "X-CSRFToken": token } : {},
    });
    if (response.ok && data) return { ok: true, data };
    return { ok: false, failure: toApiFailure(response.status, error) };
  } catch {
    return { ok: false, failure: networkFailure() };
  }
}

export async function logout(deps: SessionDeps): Promise<ActionResult<null>> {
  try {
    const token = await ensureCsrfToken(deps);
    const { error, response } = await deps.api.POST("/api/v1/auth/logout", {
      headers: token ? { "X-CSRFToken": token } : {},
    });
    if (response.ok) return { ok: true, data: null };
    return { ok: false, failure: toApiFailure(response.status, error) };
  } catch {
    return { ok: false, failure: networkFailure() };
  }
}

export function announceSessionChange(): void {
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}
