// Live two-user cache-leak check against a running stack through the proxy
// (ADR 0001 cache rules, P1-03 acceptance). Not part of `npm run web:test`;
// run with `npm run web:cache-leak` and these environment variables:
//   CACHE_LEAK_BASE_URL   e.g. http://127.0.0.1:8480 (the proxy origin)
//   CACHE_LEAK_A_EMAIL / CACHE_LEAK_B_EMAIL   two synthetic users with different roles/branches
//   CACHE_LEAK_PASSWORD   shared local password, or CACHE_LEAK_A_PASSWORD / CACHE_LEAK_B_PASSWORD
//   CACHE_LEAK_GUEST_EMAIL (optional) an authenticated account without a role
// Passwords are read from the environment only and never printed.
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const BASE = process.env.CACHE_LEAK_BASE_URL ?? "";
const A_EMAIL = process.env.CACHE_LEAK_A_EMAIL ?? "";
const B_EMAIL = process.env.CACHE_LEAK_B_EMAIL ?? "";
const GUEST_EMAIL = process.env.CACHE_LEAK_GUEST_EMAIL ?? "";
const passwordFor = (which: "A" | "B" | "GUEST") =>
  process.env[`CACHE_LEAK_${which}_PASSWORD`] ?? process.env.CACHE_LEAK_PASSWORD ?? "";

const enabled = Boolean(BASE && A_EMAIL && B_EMAIL && passwordFor("A") && passwordFor("B"));

type Jar = Map<string, string>;

interface Me {
  user: { email: string; full_name: string };
  role: string;
  branches: { name: string; code: string }[];
}

interface Session {
  jar: Jar;
  me: Me;
}

function storeCookies(jar: Jar, response: Response) {
  for (const header of response.headers.getSetCookie()) {
    const [pair] = header.split(";");
    const index = pair?.indexOf("=") ?? -1;
    if (!pair || index <= 0) continue;
    const name = pair.slice(0, index).trim();
    const value = pair.slice(index + 1).trim();
    if (value === "" || /max-age=0/i.test(header)) jar.delete(name);
    else jar.set(name, value);
  }
}

function cookieHeader(jar: Jar): Record<string, string> {
  return jar.size ? { Cookie: [...jar].map(([name, value]) => `${name}=${value}`).join("; ") } : {};
}

async function call(path: string, jar: Jar, init: RequestInit = {}) {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    redirect: "manual",
    headers: { ...cookieHeader(jar), ...(init.headers as Record<string, string> | undefined) },
  });
  storeCookies(jar, response);
  return response;
}

async function login(email: string, password: string): Promise<Session> {
  const jar: Jar = new Map();
  expect((await call("/api/v1/auth/csrf", jar)).status).toBe(204);
  const response = await call("/api/v1/auth/login", jar, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": jar.get("csrftoken") ?? "", Origin: BASE },
    body: JSON.stringify({ email, password }),
  });
  expect(response.status, `login for ${email}`).toBe(200);
  const me = (await response.json()) as Me;
  return { jar, me };
}

async function logout(session: Session) {
  await call("/api/v1/auth/csrf", session.jar);
  await call("/api/v1/auth/logout", session.jar, {
    method: "POST",
    headers: { "X-CSRFToken": session.jar.get("csrftoken") ?? "", Origin: BASE },
  });
}

interface AccountSnapshot {
  html: string;
  rsc: string;
  htmlCacheControl: string;
  rscCacheControl: string;
}

async function fetchAccount(jar: Jar): Promise<AccountSnapshot> {
  const htmlResponse = await call("/account", jar, { headers: { Accept: "text/html" } });
  expect(htmlResponse.status).toBe(200);
  const rscResponse = await call(`/account?_rsc=leak${Date.now()}`, jar, { headers: { RSC: "1" } });
  expect(rscResponse.status).toBe(200);
  expect(rscResponse.headers.get("content-type") ?? "").toContain("text/x-component");
  return {
    html: await htmlResponse.text(),
    rsc: await rscResponse.text(),
    htmlCacheControl: htmlResponse.headers.get("cache-control") ?? "",
    rscCacheControl: rscResponse.headers.get("cache-control") ?? "",
  };
}

/** Values that identify `owner` and do not also belong to `other`. */
function uniqueMarkers(owner: Me, other: Me | null): string[] {
  const otherValues = new Set(
    other ? [other.user.email, other.user.full_name, ...other.branches.map((b) => b.name)] : [],
  );
  return [owner.user.email, owner.user.full_name, ...owner.branches.map((b) => b.name)].filter(
    (value) => value && !otherValues.has(value),
  );
}

function expectContainsNone(snapshot: AccountSnapshot, markers: string[], label: string) {
  for (const marker of markers) {
    expect(snapshot.html.includes(marker), `${label} HTML leaks "${marker}"`).toBe(false);
    expect(snapshot.rsc.includes(marker), `${label} RSC leaks "${marker}"`).toBe(false);
  }
}

function expectNotPubliclyCacheable(cacheControl: string, label: string) {
  const value = cacheControl.toLowerCase();
  expect(value, `${label} Cache-Control`).toMatch(/no-store|private/);
  expect(value, `${label} Cache-Control`).not.toMatch(/\bpublic\b|s-maxage/);
}

// `npm run web:cache-leak` sets CACHE_LEAK_REQUIRED=1 so a missing configuration
// fails loudly instead of being reported as skipped.
it.runIf(Boolean(process.env.CACHE_LEAK_REQUIRED) && !enabled)("cache-leak check is configured", () => {
  expect.fail("Set CACHE_LEAK_BASE_URL, CACHE_LEAK_A_EMAIL, CACHE_LEAK_B_EMAIL and a password variable");
});

describe.skipIf(!enabled)("two-user sequential cache-leak check (live, through the proxy)", () => {
  let a: Session;
  let b: Session;
  const snapshots: Record<string, AccountSnapshot> = {};

  beforeAll(async () => {
    a = await login(A_EMAIL, passwordFor("A"));
    snapshots.a = await fetchAccount(a.jar);
    b = await login(B_EMAIL, passwordFor("B"));
    snapshots.b = await fetchAccount(b.jar);
    snapshots.aAgain = await fetchAccount(a.jar);
    snapshots.anonymous = await fetchAccount(new Map());
  });

  afterAll(async () => {
    if (a) await logout(a);
    if (b) await logout(b);
  });

  it("uses two users that differ", () => {
    expect(a.me.user.email).not.toBe(b.me.user.email);
    expect(uniqueMarkers(a.me, b.me).length).toBeGreaterThan(0);
    expect(uniqueMarkers(b.me, a.me).length).toBeGreaterThan(0);
  });

  it("renders each user's own data (positive control)", () => {
    for (const [session, snapshot] of [
      [a, snapshots.a],
      [b, snapshots.b],
    ] as const) {
      expect(snapshot!.html).toContain(session.me.user.email);
      expect(snapshot!.rsc).toContain(session.me.user.email);
      for (const branch of session.me.branches) expect(snapshot!.html).toContain(branch.name);
    }
  });

  it("second user's HTML and RSC contain none of the first user's data", () => {
    expectContainsNone(snapshots.b!, uniqueMarkers(a.me, b.me), "user B");
  });

  it("first user's later HTML and RSC contain none of the second user's data", () => {
    expectContainsNone(snapshots.aAgain!, uniqueMarkers(b.me, a.me), "user A (again)");
  });

  it("anonymous /account contains neither user's data and prompts to sign in", () => {
    expectContainsNone(snapshots.anonymous!, [...uniqueMarkers(a.me, null), ...uniqueMarkers(b.me, null)], "anonymous");
    expect(snapshots.anonymous!.html).toContain("Necesita iniciar sesión");
  });

  it("authenticated responses are not publicly cacheable", () => {
    for (const [label, snapshot] of Object.entries(snapshots)) {
      expectNotPubliclyCacheable(snapshot.htmlCacheControl, `${label} /account HTML`);
      expectNotPubliclyCacheable(snapshot.rscCacheControl, `${label} /account RSC`);
    }
  });

  it("the API marks /auth/me private and no-store", async () => {
    const response = await call("/api/v1/auth/me", a.jar);
    expect(response.status).toBe(200);
    expect((response.headers.get("cache-control") ?? "").toLowerCase()).toContain("no-store");
    expect((response.headers.get("vary") ?? "").toLowerCase()).toContain("cookie");
  });

  it.skipIf(!GUEST_EMAIL)("an authenticated account without a role is shown signed in, not anonymous", async () => {
    const guest = await login(GUEST_EMAIL, passwordFor("GUEST"));
    try {
      expect(guest.me.role).toBe("GUEST");
      const snapshot = await fetchAccount(guest.jar);
      expect(snapshot.html).toContain("Cuenta sin acceso asignado");
      expect(snapshot.html).toContain(guest.me.user.email);
      expect(snapshot.html).not.toContain("Necesita iniciar sesión");
      expectContainsNone(snapshot, [...uniqueMarkers(a.me, guest.me), ...uniqueMarkers(b.me, guest.me)], "guest");
    } finally {
      await logout(guest);
    }
  });
});
