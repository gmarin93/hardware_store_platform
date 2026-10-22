import { networkFailure, toApiFailure, type ApiFailure } from "@hardware-store/api-client";

export type Result<T> = { ok: true; data: T } | { ok: false; failure: ApiFailure };

interface FetchOutcome<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/** Converts an openapi-fetch outcome (or thrown network error) into a Result. */
export async function settle<T>(call: () => Promise<FetchOutcome<T>>): Promise<Result<T>> {
  let outcome: FetchOutcome<T>;
  try {
    outcome = await call();
  } catch {
    return { ok: false, failure: networkFailure() };
  }
  if (outcome.response.ok && outcome.data !== undefined) {
    return { ok: true, data: outcome.data };
  }
  return { ok: false, failure: toApiFailure(outcome.response.status, outcome.error) };
}
