// Server-only API clients. `publicApi` never sends cookies and may be cached;
// `sessionApi` forwards only the allowlisted session/CSRF cookies and is
// always `no-store` (it also makes the calling route dynamic via cookies()).
import { createApiClient, type ApiClient } from "@hardware-store/api-client";
import { cookies } from "next/headers";

import { getApiInternalUrl } from "./config";
import { buildForwardedCookieHeader } from "./cookies";
import { createServerFetch } from "./server-fetch";

/** Seconds anonymous catalog data may be served from the Next.js data cache. */
export const PUBLIC_CATALOG_REVALIDATE_SECONDS = 60;

export function publicApi(): ApiClient {
  return createApiClient({
    baseUrl: getApiInternalUrl(),
    fetch: createServerFetch({ kind: "public", revalidateSeconds: PUBLIC_CATALOG_REVALIDATE_SECONDS }),
  });
}

export async function sessionApi(): Promise<ApiClient> {
  const store = await cookies();
  return createApiClient({
    baseUrl: getApiInternalUrl(),
    fetch: createServerFetch({ kind: "session", cookieHeader: buildForwardedCookieHeader(store.getAll()) }),
  });
}
