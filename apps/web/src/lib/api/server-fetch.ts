// Fetch adapter used by the server-side API clients. It rebuilds every
// outbound request from scratch so no inbound header (Host, X-Forwarded-*,
// Authorization, arbitrary cookies) can reach Django, and it enforces the
// cache rule: anonymous requests may use the Next.js data cache, any request
// that carries a cookie is `no-store`.

export type ServerFetchMode =
  | { kind: "public"; revalidateSeconds: number }
  | { kind: "session"; cookieHeader: string | null };

export const SERVER_FETCH_TIMEOUT_MS = 8000;

type BaseFetch = (input: string, init: RequestInit) => Promise<Response>;

/** Methods a server fetch may use. Login/logout are browser-only (never on users' behalf). */
const SAFE_METHODS = new Set(["GET", "HEAD"]);

export function buildServerRequestInit(request: Request, mode: ServerFetchMode): RequestInit {
  const method = request.method.toUpperCase();
  if (!SAFE_METHODS.has(method)) {
    throw new Error(`Server API fetches are read-only; refused ${method} ${new URL(request.url).pathname}`);
  }
  const headers = new Headers({ Accept: "application/json" });
  const init: RequestInit = {
    method,
    headers,
    redirect: "manual",
    signal: AbortSignal.timeout(SERVER_FETCH_TIMEOUT_MS),
  };
  if (mode.kind === "session") {
    if (mode.cookieHeader) headers.set("Cookie", mode.cookieHeader);
    init.cache = "no-store";
  } else {
    init.next = { revalidate: mode.revalidateSeconds };
  }
  return init;
}

export function createServerFetch(
  mode: ServerFetchMode,
  baseFetch: BaseFetch = (input, init) => fetch(input, init),
): (request: Request) => Promise<Response> {
  return (request) => baseFetch(request.url, buildServerRequestInit(request, mode));
}
