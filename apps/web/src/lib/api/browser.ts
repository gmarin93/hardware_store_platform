// Browser-side client: same origin through the local proxy (/api/v1/*).
import { createApiClient, type ApiClient } from "@hardware-store/api-client";

let client: ApiClient | null = null;

export function browserApi(): ApiClient {
  client ??= createApiClient({ baseUrl: "", credentials: "same-origin" });
  return client;
}

/** Reads the Django CSRF cookie from a `document.cookie` string. */
export function readCsrfToken(cookieString: string): string | null {
  for (const part of cookieString.split(";")) {
    const [rawName, ...rest] = part.split("=");
    if (rawName?.trim() === "csrftoken") {
      const value = rest.join("=").trim();
      return value.length > 0 ? value : null;
    }
  }
  return null;
}
