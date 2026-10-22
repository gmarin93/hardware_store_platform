// Pure helpers for server-to-API requests (ADR 0001 "Same-origin runtime,
// sessions and cache"). Only the Django session and CSRF cookies may be
// forwarded; inbound request headers are never copied.

/** The only inbound cookies a server fetch may forward to Django. */
export const FORWARDED_COOKIE_NAMES = ["sessionid", "csrftoken"] as const;

const ALLOWED = new Set<string>(FORWARDED_COOKIE_NAMES);

// Django session keys and CSRF tokens are alphanumeric. Anything else
// (separators, whitespace, control characters) is dropped, never re-encoded.
const COOKIE_VALUE_RE = /^[A-Za-z0-9._:-]{1,512}$/;

export interface CookieLike {
  name: string;
  value: string;
}

/**
 * Builds the Cookie header for an API request from inbound cookies, keeping
 * only allowlisted names with safe values (first occurrence wins). Returns
 * null when nothing may be forwarded.
 */
export function buildForwardedCookieHeader(cookies: Iterable<CookieLike>): string | null {
  const picked = new Map<string, string>();
  for (const { name, value } of cookies) {
    if (!ALLOWED.has(name) || picked.has(name) || !COOKIE_VALUE_RE.test(value)) continue;
    picked.set(name, value);
  }
  const parts = FORWARDED_COOKIE_NAMES.filter((name) => picked.has(name)).map(
    (name) => `${name}=${picked.get(name)}`,
  );
  return parts.length > 0 ? parts.join("; ") : null;
}
