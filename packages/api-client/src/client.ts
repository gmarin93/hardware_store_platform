// Thin typed wrapper over openapi-fetch. Transport only: no authorization,
// pricing, stock or other business rules live here.
import createClient, { type Client, type ClientOptions } from "openapi-fetch";

import type { paths } from "./generated/openapi";

export type ApiClient = Client<paths>;

export interface ApiClientOptions {
  /**
   * Origin of the API. Paths in the contract already include `/api/v1`.
   * Browser code passes "" (same origin through the proxy); server code passes
   * the internal origin (e.g. http://api:8000).
   */
  baseUrl: string;
  /** Custom fetch, e.g. to add cache options or for tests. */
  fetch?: ClientOptions["fetch"];
  /** Static headers for every request (never inbound request headers). */
  headers?: Record<string, string>;
  /** Browser credential mode; defaults to "same-origin". */
  credentials?: RequestCredentials;
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  return createClient<paths>({
    baseUrl: options.baseUrl,
    fetch: options.fetch,
    credentials: options.credentials ?? "same-origin",
    headers: { Accept: "application/json", ...options.headers },
  });
}
