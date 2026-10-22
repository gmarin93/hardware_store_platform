# ADR 0001 — Phase 0 technical defaults and P1 contract freeze

- Status: accepted 2026-10-21. Owner confirmed D02 (one business, multiple branches), D03 (Spanish first), D10 (Django sessions with CSRF) and D11 (roles: admin, employee, customer, guest). Technical defaults remain reversible while no real data exists.
- Inputs: coordinator repository inspection; platform-architect and security-reviewer Phase 0 reviews (read-only, no code existed).
- Contract revision: **P1 contract rev 0.1.0** (`info.version` of the future OpenAPI export).

## Context

The repository holds only the planning package (commit `b38f1d7`, tracked on `origin/main`). There is no application, data source, integration, CI configuration or lockfile. Local toolchain observed: Python 3.13.0, uv 0.11.28, Node v20.19.2, npm 10.8.2, Docker 29.2.1, Homebrew psql client 14.13; pnpm absent. No network or registry lookup was performed, so no package versions are chosen here.

## Decisions

### Tooling

| Concern | Choice | Notes |
| --- | --- | --- |
| Python env/deps | uv, `apps/api/pyproject.toml` + `uv.lock` | Already installed |
| JS deps | npm workspaces, single root `package-lock.json` | pnpm not installed; no global installs |
| Workspaces | `apps/web`, `packages/api-client`, `tests/e2e` | Declared by P1-01 |
| OpenAPI | drf-spectacular; `spectacular --validate --fail-on-warn` | Committed `contracts/openapi.yaml` |
| TS client | openapi-typescript types + openapi-fetch; generated output committed, regenerate-and-diff check | No business rules in client |
| Backend tests | pytest + pytest-django against PostgreSQL only (no SQLite) | |
| Frontend tests | vitest; Playwright for E2E | Browser download needs authorization |
| Lint/format | ruff (lint + format); eslint (Next config) | |
| Types | mypy + django-stubs + DRF stubs; `tsc --noEmit` | |
| IDs | UUIDv4 primary keys + indexed `created_at` | Revisit v7 only with ADR |

### Version selection method (D18)

For each direct dependency, read the official support/compatibility matrix (Python↔Django↔DRF↔drf-spectacular↔psycopg; Node↔Next.js↔React; PostgreSQL major). Pick the newest mutually supported stable release, pin exactly, commit lockfiles and record source URL and access date in ADR 0002. P1-01 must verify whether local Node v20.19.2 satisfies the selected Next.js minimum and whether it is still supported; if not, run Node in a pinned Compose image or ask the owner to install an LTS — agents do not install global runtimes. Use database client tools inside the Postgres container, not the host psql 14.

Registry access, image pulls and Playwright browser downloads during P1-01 require explicit owner authorization for network use (CLAUDE.md).

### Same-origin runtime, sessions and cache

- A pinned reverse proxy in Compose (`infra/local/`) exposes one localhost origin. Only `/api/v1/*` routes to a fixed Django upstream; everything else to Next.js. No path-derived upstream hosts. Django admin is not routed (see below).
- Postgres is not published, or is bound to 127.0.0.1 only.
- Django DB-backed sessions. Session cookie HttpOnly, SameSite=Lax, Secure outside local. CSRF cookie readable by JS, sent as `X-CSRFToken`. `GET /auth/csrf` sets it. Login and logout (POST only) enforce CSRF; login rotates the session key, logout flushes it. Explicit `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`; forwarded headers trusted only from the proxy.
- Next.js server fetches go to Django on the internal network forwarding only the session and CSRF cookies; `Set-Cookie` returns only to the originating response. Any fetch carrying a cookie is `cache: 'no-store'`/dynamic. Public catalog pages fetch anonymously (no cookies) and may be cached.
- Django sends `Cache-Control: private, no-store` and `Vary: Cookie` on authenticated responses.
- Basic login throttling ships in P1. Never log cookies, CSRF tokens or passwords.

### Django admin

Not mounted in P1. If later enabled, only on a localhost-bound port never routed through the proxy. No seeded superuser; `is_superuser` is not a business role and grants no cross-organization access.

### Secrets and demo users

Only a synthetic `.env.example` with obvious placeholders. Settings refuse to start when DEBUG is off and `SECRET_KEY` is the placeholder. Demo users are created only by an explicit local-only management command that generates or prompts for passwords; no fixed passwords committed.

### Identity, roles and scope

- Roles (owner-confirmed): GUEST (unauthenticated, not stored), CUSTOMER, EMPLOYEE, ADMIN. Matrix in DOMAIN_CONTRACTS.md.
- EMPLOYEE: `BranchMembership(user, branch)`; an employee may belong to several branches. No sales/warehouse/manager sub-roles.
- ADMIN: organization-level `RoleAssignment` over all branches of the one business; never crosses organizations.
- Customer: `CustomerProfile(organization)`, no branch.
- Services check named permission codes (e.g. `catalog.view_staff_fields`), not role names scattered in views. Roles map to default permission sets so a future split of EMPLOYEE stays additive.
- Scope is resolved on every request from active memberships through scoped selectors/querysets; never from serializers or client `branch_id`. Revoked membership or deactivated user loses access on the next request.
- Single-org MVP: guests resolve `DEFAULT_ORGANIZATION_SLUG`. Test fixtures always include a second synthetic organization so cross-org denial is testable.
- Customer accounts in P1 come only from fixtures/management command. Self-registration needs an owner decision before P3 (D19).

### HTTP status and error envelope

| Case | Status | code |
| --- | --- | --- |
| Unauthenticated on protected endpoint | 401 | NOT_AUTHENTICATED (custom handler; DRF session auth defaults to 403) |
| Object outside actor's org/branch/ownership, or unpublished for guest/customer | 404, body identical to a nonexistent UUID | NOT_FOUND |
| Branch selector not visible to actor | 404 | NOT_FOUND |
| Visible object, action not permitted | 403 | PERMISSION_DENIED |
| CSRF failure (incl. login/logout) | 403 | CSRF_FAILED |
| Bad credentials (unknown user or wrong password, uniform) | 400 | INVALID_CREDENTIALS |
| Throttled | 429 | THROTTLED |

List endpoints filter silently. Envelope: `{code, message, field_errors, request_id}`; `code` stable UPPER_SNAKE; `message` localized es-CR; `field_errors` is `{field: [{code, message}]}` or `{}`; `request_id` taken from a valid inbound `X-Request-ID` or generated UUID and echoed as a response header.

### Pagination

Opaque `cursor`; `page_size` default 20, max 100; response `{results, next_cursor, previous_cursor}`; ordering always ends with `id`. P2 relevance search must define a `(rank, id)` cursor or bounded result set (flagged for P2 planning).

### Catalog and units (P1 scope)

- Product = family; Variant = SKU. `status` on both: DRAFT, PUBLISHED, ARCHIVED.
- Quantities `NUMERIC(14,3)`, decimal strings in API. Unit enum: `piece, m, cm, kg, g, l`.
- Variant: `sales_unit`, `stock_unit`, `quantity_increment > 0`, `min_quantity`. P1 enforces `sales_unit == stock_unit` with a DB constraint; conversions deferred to a P3 ADR. Non-multiple quantities rejected with `INVALID_QUANTITY_INCREMENT`, never rounded.
- Product dimensions are typed `AttributeValue(value, unit)`, separate from sales/stock units.
- Public serializer allowlist: id, sku, name, description, brand, category, published attributes, approved media, units, increment, min_quantity. Staff-only: SourceReference/provenance, source URLs, unpublished records, draft media, internal notes, supplier codes. Separate serializers and OpenAPI components; tests assert exact key sets.
- P1 catalog API exposes **no price and no availability fields or endpoints** (D07/D09 pending).
- Endpoints: `GET /catalog/products` (filters, cursor), `GET /catalog/products/{id}` (variants embedded), `GET /catalog/variants/{id}`, `GET /catalog/variants?sku=` exact match. Web route `/catalog/[sku]` resolves via the exact SKU filter.

### Synthetic fixtures

Fixture records carry `is_synthetic=true` (organization and source). Fictitious names, `example.test` emails, "SINTÉTICO" labels and a visible "Datos de demostración" UI banner. Loader refuses to run outside local/test settings. Remote fetch/scraping is not permitted in any phase until D04 is resolved.

### Deferred technical defaults (recorded now, applied later)

- Money (P3): unit prices `NUMERIC(18,4)`, line/document amounts scale 2, ROUND_HALF_UP, line-level rounding, tax-exclusive — labeled synthetic/non-production until D09 is confirmed.
- Idempotency (P3-01, before P3-03): key 1–128 chars; missing → 400 `IDEMPOTENCY_KEY_REQUIRED`; different payload → 409 `IDEMPOTENCY_KEY_REUSED`; concurrent identical request waits on the row lock and receives the original response; retention 7 days with cleanup command; business uniqueness remains the backstop.
- Search/queues: Postgres exact/full-text/trigram first (D14).

## Alternatives considered

pnpm (not installed, no global install permitted); SQLite tests (cannot prove Postgres locking/constraints); Next.js rewrites as the only proxy (harder to keep admin and arbitrary paths unroutable); UUIDv7 (no stdlib support in Python 3.13, Postgres version not chosen).

## Consequences and validation

P1 tasks must implement and test each item above; ADR 0002 records exact versions. Changing the custom user model or UUID choice after P1 migrations requires rebuilding the local database — acceptable only while no real data exists.
