# ADR 0003 — Identity, scope, permission codes and API error conventions (P1-02A)

- Status: accepted for P1 contract rev 0.1.0 (2026-10-21). Implements ADR 0001 "Sessions", "Identity, roles and scope", "HTTP status and error envelope" and "Pagination"; no ADR 0001 decision is changed.
- Owner: django-domain (P1-02A). Reversible while only synthetic data exists; changing the user model or UUID keys afterwards means rebuilding the local database.

## Identity

- `accounts.User` (`AUTH_USER_MODEL = "accounts.User"`): UUIDv4 primary key, `email` is the login (`USERNAME_FIELD`), stored lowercase (normalized in `save()`/manager; DB check constraint `accounts_user_email_lowercase`), `full_name`, `is_active`, `is_staff`, indexed `created_at`. `PermissionsMixin` is kept only for Django compatibility: `is_superuser`, `is_staff`, groups and Django model permissions grant **nothing** business-wise and are never read by scope code.
- Users without a password get an unusable password and cannot log in. Password validators: Django's four defaults with a 12-character minimum (used by future management commands; there is no self-registration, D19).
- `accounts.CustomerProfile(user 1:1, organization)` makes a user a CUSTOMER.
- `organizations.Organization(slug unique, name, is_synthetic, is_active)`, `Branch(organization, code unique per organization, name, is_active)`, `BranchMembership(user, branch, is_active)` unique per (user, branch), `RoleAssignment(user, organization, role=ADMIN, is_active)` unique per (user, organization, role) with a DB check that `role` is known.
- `DEFAULT_ORGANIZATION_SLUG` (env `DJANGO_DEFAULT_ORGANIZATION_SLUG`, default `demo`) is the organization guests resolve to.

## Roles and actor resolution

Resolved on every request by `organizations.scope.resolve_actor` from active rows only (active user, organization, branch, membership/assignment). Nothing comes from the session payload, serializers or client `branch_id`.

1. Candidate organizations = organizations of active ADMIN assignments ∪ active memberships ∪ customer profile.
2. Not exactly one candidate → the account has no business role and is treated as **GUEST** (fail closed; a multi-organization account is logged by user id only).
3. Within that organization: ADMIN (all active branches) > EMPLOYEE (active member branches) > CUSTOMER (no branches).
4. Anonymous → GUEST with the default organization.

**GUEST for authenticated accounts:** an authenticated user without a valid role (superuser without assignments, revoked employee, ambiguous account) is reported by `GET auth/me` as `role: "GUEST"` with guest permissions. The session is still authenticated: the frontend must not treat this as anonymous (it must still offer logout and must not show the login form as if signed out); it should present "account without access".

Consequences: revoking a membership/assignment or deactivating an organization/branch takes effect on the next request; a deactivated user's existing session becomes anonymous (Django `ModelBackend.get_user`) → 401.

## Permission codes

Single source: `apps/api/accounts/permissions.py` (`Role`, `Perm`, `ROLE_PERMISSIONS`). Services check codes via `Actor.has_perm` / `common.permissions.require_perm`, never role names.

| Code | GUEST | CUSTOMER | EMPLOYEE | ADMIN | Enforced from |
| --- | --- | --- | --- | --- | --- |
| `catalog.view_published` | x | x | x | x | P1-02B |
| `catalog.view_staff_fields` | | | x | x | P1-02B |
| `branches.view_assigned` | | | x | | P1-02A (`visible_branches`) |
| `branches.view_all` | | | | x | P1-02A (`visible_branches`) |
| `quotes.request_own`, `quotes.accept_own` | | x | | | reserved P3 |
| `quotes.manage`, `quotes.issue`, `quotes.record_customer_consent`, `quotes.convert` | | | x | x | reserved P3 |
| `inventory.view_internal`, `inventory.report_discrepancy` | | | x | x | reserved P2/P3 |
| `orders.pick`, `orders.fulfill`, `orders.cancel` | | | x | x | reserved P3 |
| `inventory.adjust`, `pricing.manage`, `staff.manage`, `audit.view` | | | | x | reserved; `staff.manage` exercised by a test-only probe |

Reserved codes are frozen names; the owning task enforces them and adds direct API tests. Adding or splitting codes is additive (matrix update + tests).

## Scope helpers (`organizations/scope.py`, `common/permissions.py`)

- `get_request_actor(request)`: per-request cache, recomputed every request.
- `GET branches/{id}` uses a `str` path converter so malformed IDs reach the view and produce the same DRF NotFound response (body and headers) as nonexistent and out-of-scope IDs. Endpoints using Django's `uuid` converter would instead fall through to the JSON catch-all 404, whose body is identical but whose headers differ (no `Allow`); resource-by-id endpoints should use the `str` pattern.
- `visible_branches(actor)`, `get_visible_branch(actor, raw_id)`: malformed, nonexistent, inactive, non-member and other-organization IDs all raise the same `NotFound`.
- `scope_to_organization(qs, actor, field)`, `scope_to_visible_branches(qs, actor, field)`, `get_scoped_object_or_404(scoped_qs, raw_id)`.
- Check order in a view/service: authentication (401) → scoped lookup (404) → `require_perm` on the visible object (403). List endpoints filter silently (customers get `[]` from `GET /branches`).
- `HasPermissionCodes` DRF permission (view attribute `required_permissions`) for endpoints where a missing code is 403 rather than an empty result.

## Sessions, CSRF and throttling

- `common.authentication.SessionAuthentication` returns `WWW-Authenticate: Session`, so unauthenticated requests are **401 NOT_AUTHENTICATED** (DRF's default would be 403). No browser credential prompt is triggered.
- CSRF failures raise `CsrfFailed` → **403 CSRF_FAILED**. DRF only enforces CSRF for authenticated sessions; `EnforceCsrfMixin` enforces it for unsafe methods on login and logout regardless of authentication, before throttling. Django's token and Origin checks are used unchanged (`CSRF_TRUSTED_ORIGINS`, same host). The token is accepted only from the `X-CSRFToken` header; form bodies are not parsed for `csrfmiddlewaretoken` (keeps JSON-only endpoints answering 415 for form posts). `CSRF_FAILURE_VIEW` returns the same envelope for non-DRF views.
- Endpoints (all under `/api/v1/`): `GET auth/csrf` (204, sets cookie), `POST auth/login` `{email, password}` → 200 me payload, `POST auth/logout` → 204 (GET → 405), `GET auth/me` → `{user{id,email,full_name}, organization{id,slug,name,is_synthetic}|null, role, branches[{id,code,name}], permissions[]}`, `GET branches` (cursor), `GET branches/{uuid}`.
- Login uses `django.contrib.auth.authenticate/login` (session key cycled, CSRF token rotated; client must re-read the `csrftoken` cookie). Logout calls `logout()` (session flushed). Unknown email, wrong password, inactive user and unusable password all return the identical **400 INVALID_CREDENTIALS** body; `ModelBackend` hashes a dummy password for unknown users. Missing/blank fields are 400 VALIDATION_ERROR (before authentication).
- Throttles (every attempt counts): `login_ip` 20/min per client address and `login_account` 5/min per SHA-256 of the normalized email → **429 THROTTLED** with `Retry-After`. Cache is per-process LocMem: with N gunicorn workers the effective limit is up to N× (accepted for P1; a shared cache is a later change).
- Client address (`common.client_ip.client_ip`): `X-Forwarded-For` (last entry, must parse as an IP) is trusted only when `REMOTE_ADDR` belongs to `TRUSTED_PROXY_HOSTS` (env `DJANGO_TRUSTED_PROXY_HOSTS`, comma-separated IPs, CIDRs or hostnames; default `proxy`, the Compose service; hostnames resolved and cached 60 s; unresolvable names trust nothing). Any other peer, such as the web container calling `api:8000` directly, is keyed by `REMOTE_ADDR`. DRF's `NUM_PROXIES` is `0`, so other DRF throttles never parse `X-Forwarded-For`.
- **Accepted risk — targeted lockout:** the per-account limit is reachable unauthenticated, so anyone knowing an email can keep that account at 429 for login (5 attempts/min). Accepted for P1 (synthetic users, no self-registration); revisit with a shared cache, failure-only counting or progressive delays before real accounts exist.

## Error envelope

`{code, message, field_errors, request_id}` from `common.exceptions.api_exception_handler` for every DRF error, plus `common.views` for unknown API paths (catch-all route, any method, CSRF-exempt because it mutates nothing), `handler404`, `handler500` and CSRF failures. Bodies are rendered identically (compact JSON), so an out-of-scope object, a nonexistent UUID, a malformed UUID path and an unknown path give the same NOT_FOUND body (apart from `request_id`).

| Status | code |
| --- | --- |
| 400 | VALIDATION_ERROR, PARSE_ERROR, INVALID_CREDENTIALS, INVALID_CURSOR |
| 401 | NOT_AUTHENTICATED |
| 403 | PERMISSION_DENIED, CSRF_FAILED |
| 404 | NOT_FOUND |
| 405 | METHOD_NOT_ALLOWED |
| 406 / 415 | NOT_ACCEPTABLE / UNSUPPORTED_MEDIA_TYPE |
| 429 | THROTTLED |
| 500 | INTERNAL_ERROR (transaction marked for rollback; exception class and request id logged; no detail returned) |

- `message` is a fixed es-CR text per code (`common/errors.py`); DRF/Django English and exception details are never echoed. `field_errors` is `{path: [{code, message}]}` (dotted paths for nested data, `non_field_errors` for object-level errors) or `{}`; field messages are DRF's Spanish translations.
- `request_id`: inbound `X-Request-ID` reused when it matches `^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$`, otherwise a UUIDv4; echoed as `X-Request-ID` and added to log records (`[%(request_id)s]`).
- New codes are added in `common/errors.py` (code + es-CR message) and raised as `CodedAPIException` subclasses.
- OpenAPI: `common.schema.ErrorEnvelopeSerializer` component and `error_responses(*statuses)` helper; `SessionCookieScheme` documents the session cookie. `spectacular --validate --fail-on-warn` passes.

## Pagination

`common.pagination.CursorPagination` (DRF default pagination class): keyset over `view.cursor_ordering` (default `("-created_at", "-id")`), which must consist of direct non-null attributes and end with `id`/`-id`. Cursor = signed (`django.core.signing`, salt `common.pagination.cursor`) list of boundary values + direction; tampered/stale → 400 INVALID_CURSOR. `page_size` default 20, values > 100 clamped to 100, non-integer/< 1 → 400 VALIDATION_ERROR. Response `{results, next_cursor, previous_cursor}`. Cursors carry no authorization; rows always come from the scoped queryset. Cursors are **signed, not encrypted**: the boundary values are readable by base64-decoding. Public or customer-facing endpoints must never order by staff-only or unpublished fields (e.g. provenance, internal notes, cost), because the cursor would disclose them. Relevance ordering (P2) still needs its own `(rank, id)` design.

## Cache headers and logging

- `SessionCacheHeadersMiddleware` (outermost) adds `Vary: Cookie` to every response and `Cache-Control: private, no-store` when the user is authenticated, the request carries a session cookie, or the response sets any cookie.
- Application logs contain user ids only; `django.request` logs method/path. Django's default `django` handlers (including `mail_admins`, which would include request data) are removed so records go once through the root handler. Tests assert passwords, session keys and CSRF tokens never appear in captured logs, with DEBUG off and on.
- `django.db.backends` is pinned to WARNING, so SQL with parameters (password hashes, session data) is not logged even when `DEBUG=True`.
- `common.log_filters.SensitiveRecordFilter` (logger-level): `django.security.csrf` records are rewritten to `Forbidden (CSRF): <path>` (Django's reason embeds the raw Origin/Referer); `django.request` records lose `exc_info` (message and traceback) and keep the exception class name when DEBUG is off.
- Unexpected API exceptions: the handler calls DRF `set_rollback()` (an `ATOMIC_REQUESTS` transaction is rolled back) and logs only exception class, view and request id at ERROR; the traceback is logged at DEBUG only when `settings.DEBUG` is on (local development).

## Alternatives considered

- DRF `CursorPagination`: positions on the first ordering field plus an offset, so it does not honour the `(…, id)` tiebreak contract precisely; replaced by a keyset implementation.
- DB-backed throttle table or cache: needs an extra migration/`createcachetable`; deferred until a shared cache exists.
- Role-name checks in views: rejected (ADR 0001); codes keep a future EMPLOYEE split additive.
- Treating an ambiguous multi-organization account by precedence: rejected in favour of fail-closed GUEST.
