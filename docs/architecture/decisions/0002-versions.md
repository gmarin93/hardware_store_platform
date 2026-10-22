# ADR 0002 — Pinned runtime and dependency versions (P1-01)

- Status: proposed 2026-10-21 by P1-01 (runtime-engineer); awaiting coordinator review.
- Method: ADR 0001 "Version selection method (D18)". For each direct dependency we read the official support or compatibility source, picked the newest release that every other chosen component officially supports, and pinned it exactly (no `^`/`~`). Docker images are pinned by version tag and multi-arch index digest.
- Network use: D20 (official docs, registry metadata, pinned installs and image pulls). All sources below were accessed on **2026-10-21**.
- Lockfiles: `apps/api/uv.lock` (uv 0.11.28) and the single root `package-lock.json` (lockfileVersion 3, npm 11.19.1 from the Node image).

## Decision summary

### Runtimes and images

| Component | Pin | Why this and not newer | Source |
| --- | --- | --- | --- |
| Python (container) | `python:3.13.17-slim-trixie@sha256:19ed48e5e9c132082510ba9efb11bc2098d582f610374670fa30b6b17026617b` | 3.14 and 3.15 exist, but gunicorn 26.2.0 declares support only up to 3.13 and the host has only CPython 3.13.0 (installing another interpreter would be an unapproved runtime download). 3.13 receives security fixes until 2029-10 and is supported by every package below. | https://devguide.python.org/versions/ ; https://hub.docker.com/_/python/tags ; https://pypi.org/pypi/gunicorn/26.2.0/json |
| Python (host, `.python-version`) | `3.13` | Used by `uv` for host ruff/mypy runs. Host patch is 3.13.0 (old patch); the container (3.13.17) is the reference runtime for tests. | as above |
| Node (container, `.nvmrc`) | `node:24.22.1-alpine3.24@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53` | Node 24 "Krypton" is LTS (maintenance since 2026-10-20, EOL 2028-04-30). Node 26 is still "Current" until its LTS date 2026-10-28; revisit after that. | https://raw.githubusercontent.com/nodejs/Release/main/schedule.json ; https://nodejs.org/dist/index.json ; https://hub.docker.com/_/node/tags |
| npm | `11.19.1` (bundled with the Node image; `packageManager` field) | Comes with the pinned image; no separate install. | image inspection (`npm -v`) |
| PostgreSQL | `postgres:18.6-alpine3.24@sha256:83148c0bc09eac4d598b70a61e1404d0212b76c95c504bfd6c81a4c59ec91792` | 18 is the newest supported major (until 2030-11-14). 19 is only an RC (`19rc1`). The PG 18 image stores data under `/var/lib/postgresql` (volume mounted there). | https://www.postgresql.org/support/versioning/ ; https://hub.docker.com/_/postgres/tags |
| Reverse proxy | `caddy:2.11.7-alpine@sha256:24ec7b05bc532c7bb57f727030c5056e257ff7138b4b50460306819ff79362bd` | Latest stable Caddy release (v2.11.7, 2026-10-03). | https://github.com/caddyserver/caddy/releases ; https://hub.docker.com/_/caddy/tags |
| uv (in API image) | `ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa` | Same version as the host uv that produced `uv.lock`. | https://docs.astral.sh/uv/guides/integration/docker/ (documented `COPY --from` pattern) |

Digests were confirmed after `docker pull` (`docker image inspect … RepoDigests`) to match Docker Hub/GHCR.

### Python (apps/api/pyproject.toml)

| Package | Pin | Compatibility evidence and reason | Source |
| --- | --- | --- | --- |
| Django | `6.0.9` | Django 6.1.2 is the newest release, but drf-spectacular 0.30.0 (README, tox matrix) and released pytest-django 4.14.0 officially support Django only up to 6.0; pytest-django's 6.1 support is listed as "unreleased" (4.15.0). 6.0 has extended support until **April 2027** (see upgrade trigger). Supports Python 3.12–3.14. | https://www.djangoproject.com/download/ (Supported Versions) ; https://pypi.org/pypi/django/json |
| djangorestframework | `3.17.2` | DRF 3.18.3 exists, but drf-spectacular 0.30.0 documents support for DRF 3.12–3.17 (tox tests django6.0 × drf3.17). DRF 3.17 supports Django 4.2–6.0. | https://raw.githubusercontent.com/tfranzel/drf-spectacular/master/README.rst ; https://raw.githubusercontent.com/tfranzel/drf-spectacular/master/tox.ini ; https://pypi.org/pypi/djangorestframework/3.17.1/json |
| drf-spectacular | `0.30.0` | Latest; changelog "add support for django 6.0 and drf 3.17". | https://raw.githubusercontent.com/tfranzel/drf-spectacular/master/CHANGELOG.rst |
| psycopg[binary] | `3.3.6` (psycopg-binary 3.3.6) | Latest; Python 3.10–3.15. Connectivity with PostgreSQL 18.6 verified locally by the health check and pytest (not by a published matrix). | https://pypi.org/pypi/psycopg/json ; https://psycopg.org/psycopg3/docs/news.html |
| gunicorn | `26.2.0` | Latest; WSGI server for the local API container. | https://pypi.org/pypi/gunicorn/json |
| pytest | `9.1.1` | Latest; pytest-django requires `pytest>=7`. | https://pypi.org/pypi/pytest/json |
| pytest-django | `4.14.0` | Latest released; Django 5.2/6.0 official. | https://raw.githubusercontent.com/pytest-dev/pytest-django/main/docs/changelog.rst |
| ruff | `0.17.1` | Latest. | https://pypi.org/pypi/ruff/json |
| mypy | `2.3.1` | mypy 2.4.0 exists, but django-stubs 6.0.9 (README table: mypy 1.13–2.3) and djangorestframework-stubs 3.17.1 (`compatible-mypy`: `mypy<2.4`) cap it. | https://raw.githubusercontent.com/typeddjango/django-stubs/master/README.md ; https://pypi.org/pypi/djangorestframework-stubs/3.17.1/json |
| django-stubs | `6.0.9` | Matches Django 6.0 (full support per README table). 6.1.x targets Django 6.1. | django-stubs README (above) |
| django-stubs-ext (constraint) | `6.0.9` | Transitive; constrained via `[tool.uv] constraint-dependencies` so it stays on the 6.0 series instead of resolving to 6.1.2. | https://pypi.org/pypi/django-stubs-ext/json |
| djangorestframework-stubs | `3.17.1` | Matches DRF 3.17; requires `django-stubs>=6.0.7`. 3.18.1 would require django-stubs ≥6.1.0. | https://pypi.org/pypi/djangorestframework-stubs/json |

### JavaScript (apps/web/package.json, root package.json)

| Package | Pin | Compatibility evidence and reason | Source |
| --- | --- | --- | --- |
| next | `16.4.2` | Latest stable (`latest` dist-tag). `engines.node >=20.9.0`; peer React `^18.2 \|\| ^19`. | `npm view next@16.4.2 engines peerDependencies` (https://registry.npmjs.org/next) |
| react, react-dom | `19.3.1` | Latest; within Next peer range. | https://registry.npmjs.org/react |
| typescript | `5.9.3` | TS 7.0.2 and 6.0.3 exist. typescript-eslint 8.72.0 (pulled by eslint-config-next) requires `typescript >=4.8.4 <6.1.0`, and openapi-typescript 7.13.0 (ADR 0001 client generator, P1-03) declares peer `typescript ^5.x`. 5.9.3 is the newest release satisfying both in the shared lockfile. | `npm view typescript-eslint peerDependencies` ; `npm view openapi-typescript@7.13.0 peerDependencies` |
| eslint | `10.13.0` | ESLint 9 reached EOL 2026-08-06. Next's bundled docs (node_modules/next/dist/docs/01-app/03-api-reference/05-config/03-eslint.md, also https://nextjs.org/docs/app/api-reference/config/eslint) state eslint-config-next 16.4+ supports ESLint 10, while some bundled plugins (eslint-plugin-react 7.37.5, -import 2.32.0, -jsx-a11y 6.10.2) still declare peers only up to ESLint 9. A root `overrides: {"eslint": "10.13.0"}` keeps a single ESLint copy in the tree (without it npm hoisted a second ESLint 9 to satisfy those peers). | https://eslint.org/version-support/ ; Next bundled docs (above) |
| eslint-config-next | `16.4.2` | Same release as next. Flat config `eslint-config-next/core-web-vitals` + `/typescript`. | Next bundled docs |
| vitest | `5.0.5` | Latest; `engines.node ^22.12.0 \|\| ^24.0.0 \|\| >=26.0.0`; peer vite `^6.4 \|\| ^7 \|\| ^8`. | `npm view vitest@5.0.5 engines peerDependencies` |
| vite | `8.3.5` | Latest; vitest peer. | https://registry.npmjs.org/vite |
| @types/node | `24.19.2` | Newest 24.x, matching the Node 24 runtime. | https://registry.npmjs.org/@types/node |
| @types/react, @types/react-dom | `19.3.0` | Newest for React 19.3. | https://registry.npmjs.org/@types/react |

Not installed in P1-01 (noted for P1-03/P1-04): `openapi-typescript 7.13.0`, `openapi-fetch 0.17.0`, `@playwright/test 1.64.1` (registry `latest` on 2026-10-21). P1-03 must re-check that openapi-typescript's `typescript ^5.x` peer is still compatible with the pinned TS 5.9.3; it is today.

## D22 — host Node suitability

- Host Node v20.19.2 satisfies next 16.4.2 `engines` (`>=20.9.0`) but **Node 20 reached end of life on 2026-04-30** (nodejs/Release schedule) and is below the vitest 5.0.5 minimum (`^22.12.0 || ^24 || >=26`).
- Outcome: all web tooling (install, lint, typecheck, test, build) runs in the pinned `node:24.22.1-alpine3.24` image via `infra/local/node.sh`, and the web container uses the same image. No Node was installed on the host.
- Owner action (optional): to run npm on the host, install Node 24 LTS (`.nvmrc` = `24.22.1`) yourself and run `npm ci` again, because `node_modules` installed from the container contains Linux/musl native binaries.

## Upgrade triggers

- Django 6.0 extended support ends **April 2027**. Move to Django 6.1/6.2 LTS once drf-spectacular and a released pytest-django officially support it. DRF 3.18, django-stubs 6.1 and mypy 2.4 follow in the same change.
- Node 26 becomes LTS on 2026-10-28. Consider moving after vitest/Next confirm support. Node 24 EOL is 2028-04-30.
- TypeScript ≥6: when typescript-eslint and openapi-typescript widen their peers.
- Python 3.14: when gunicorn declares support and a host 3.14 interpreter is available with owner approval.
- ESLint plugin peers: drop the root `overrides` once eslint-plugin-react/import/jsx-a11y declare ESLint 10.

## Consequences

Upgrading any pin requires updating this ADR, regenerating the lockfile in the same change and rerunning `docs/development/CHECKS.md`. Image digest pins must be refreshed deliberately; they will not pick up base-image security rebuilds by themselves.
