/**
 * Internal Django origin for server-side fetches (Compose: http://api:8000).
 * Read from the environment only; never derived from the incoming request.
 */
export function getApiInternalUrl(env: Record<string, string | undefined> = process.env): string {
  const raw = env.API_INTERNAL_URL;
  if (!raw) throw new Error("API_INTERNAL_URL is not configured");
  const url = new URL(raw);
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("API_INTERNAL_URL must be an http(s) origin");
  }
  return url.origin;
}
