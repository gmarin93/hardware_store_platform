# Local checks

Every command in the numbered tables was executed for P1-01; exit statuses are in `docs/evidence/P1-01.md`. Paths are relative to the repository root.

Prerequisites: Docker running, `uv` 0.11.28, host Python 3.13 (for host ruff/mypy). Host Node is **not** used: web tooling runs in the pinned Node 24 image via `infra/local/node.sh` (ADR 0002, D22). Never commit `.env`.

## Backend (apps/api)

| # | Working directory | Command | Checks |
| --- | --- | --- | --- |
| 1 | `apps/api` | `uv lock --check` | `uv.lock` matches `pyproject.toml` |
| 2 | `apps/api` | `uv sync --locked` | Host virtualenv (`apps/api/.venv`) installs exactly from the lockfile |
| 3 | `apps/api` | `uv run ruff check .` | Lint |
| 4 | `apps/api` | `uv run ruff format --check .` | Formatting |
| 5 | `apps/api` | `uv run mypy .` | Strict typing with django-stubs and DRF stubs (settings `config.settings.test`; no database needed) |

## Web (npm workspaces, pinned Node container)

| # | Working directory | Command | Checks |
| --- | --- | --- | --- |
| 6 | repo root | `infra/local/node.sh npm ci` | Installs from the single root `package-lock.json` (fails if the lockfile is out of sync) |
| 7 | repo root | `infra/local/node.sh npm run web:lint` | ESLint (eslint-config-next core-web-vitals + typescript) |
| 8 | repo root | `infra/local/node.sh npm run web:typecheck` | `next typegen && tsc --noEmit` |
| 9 | repo root | `infra/local/node.sh npm run web:test` | Vitest (`vitest run`) |
| 10 | repo root | `infra/local/node.sh npm run web:build` | `next build` (standalone output) |

## Runtime (disposable Compose project)

Verification uses a disposable project name and the synthetic `.env.example` so it never touches a developer's own stack or data. Set `C="docker compose --env-file .env.example -p hwp1check"` (any unused disposable name works; the security-review re-check used `hwp1fix`). Run these with bash: zsh does not word-split `$C`.

| # | Working directory | Command | Checks |
| --- | --- | --- | --- |
| 11 | repo root | `$C config --quiet` | Compose file and interpolation are valid |
| 12 | repo root | `$C up --build --wait` | db, api, web and proxy all reach `healthy` |
| 13 | repo root | `$C run --rm --no-deps api pytest` | Backend tests against PostgreSQL (pytest-django creates and drops a `test_*` database) |
| 14 | repo root | `$C run --rm --no-deps api ruff check .` | Lint inside the reference Python 3.13.17 image |
| 15 | repo root | `$C run --rm --no-deps api mypy .` | Typing inside the reference image |
| 16 | repo root | `curl -fsS http://127.0.0.1:8480/api/v1/health` | Health via the single proxy origin; expects `{"status":"ok","database":"ok"}` |
| 17 | repo root | `curl -fsS -o /dev/null http://127.0.0.1:8480/` | Next.js placeholder via the proxy |
| 18 | repo root | `test "$($C port db 5432)" = ':0'` | PostgreSQL is not published to the host |
| 19 | repo root | `test "$($C port proxy 80)" = '127.0.0.1:8480'` | Proxy bound to 127.0.0.1 only |
| 20 | repo root | `test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8480/api/v1/admin/)" = 404` | Admin is not mounted behind the API route |
| 21 | repo root | `curl -s -o /dev/null -H 'X-CSRFToken: canary123' -H 'Cookie: csrftoken=canary123' http://127.0.0.1:8480/ && test "$($C logs proxy | grep -c canary123)" = 0` | Proxy access log does not record CSRF tokens or cookies (ADR 0001) |
| 22 | repo root | `$C down -v` | Tear down **only** the disposable project and its volume |

## Everyday local use

These use your own `.env` and the default project name; P1-01 ran the equivalent commands only against the disposable `hwp1check` project.

```sh
cp .env.example .env            # synthetic placeholders; edit locally, never commit
docker compose up --build --wait
curl http://127.0.0.1:8480/api/v1/health
docker compose run --rm --no-deps api pytest
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'   # DB client inside the container
docker compose down             # keeps the pgdata volume
```

Do not run `manage.py migrate` until P1-02A has set the custom `AUTH_USER_MODEL`.

## Restore procedure

- Disposable verification stack: `docker compose --env-file .env.example -p <disposable-name> down -v` (e.g. `hwp1check`, `hwp1fix`).
- Reset your own local stack (deletes local DB data; there is no real data in P1): `docker compose down -v`, then `docker compose up --build --wait`.
- Web dependencies: delete `node_modules` and `apps/web/node_modules`, then `infra/local/node.sh npm ci`.
- Python dependencies: delete `apps/api/.venv`, then `uv sync --locked` in `apps/api`; rebuild the image with `docker compose build api`.

## P1-02B: catalog seed and OpenAPI contract

Same disposable project as above (`C="docker compose --env-file .env.example -p <disposable-name>"`, bash). `compose.yaml` mounts `tests/fixtures/synthetic` read-only into the api container (coordinator integration after P1-02B), so plain `$C run --rm --no-deps api pytest` (row 13) again runs the full suite including the seed tests. The contract directory is still mounted per command with `-v`. In the container `<repo>/tests/fixtures/synthetic/p1` resolves to `/tests/fixtures/synthetic/p1` (the seed command's default `--data-dir`).

| # | Working directory | Command | Checks |
| --- | --- | --- | --- |
| 23 | repo root | `$C run --rm --no-deps api pytest` | Full backend suite **including** the seed tests (same as row 13; they fail with a mount hint if the data directory is missing) |
| 24 | repo root | `$C run --rm --no-deps api python manage.py makemigrations --check --dry-run` | Models and migrations agree |
| 25 | repo root | `$C run --rm --no-deps -e ALLOW_SYNTHETIC_SEED=1 api python manage.py seed_synthetic` | Loads the synthetic catalog. Local only: refuses unless `DEBUG` is on or settings are `config.settings.test`, **and** `ALLOW_SYNTHETIC_SEED=1` is set, **and** no non-synthetic organization exists. Idempotent; a re-run creates nothing. Add `--with-demo-users` to create `@example.test` demo accounts: with `-it` (TTY) the generated passwords are printed once; without a TTY the accounts get unusable passwords and the command prints `manage.py changepassword <email>` steps. Passwords are stored nowhere |
| 26 | repo root | `$C run --rm --no-deps -v "$PWD/contracts:/contracts" api python manage.py spectacular --validate --fail-on-warn --file /contracts/openapi.yaml` | Regenerates the committed contract after an API change |
| 27 | repo root | `$C run --rm --no-deps -v "$PWD/contracts:/contracts:ro" api sh -c 'python manage.py spectacular --validate --fail-on-warn --file /tmp/openapi.yaml && diff -u /contracts/openapi.yaml /tmp/openapi.yaml'` | Regenerate-and-diff: exit 0 only if `contracts/openapi.yaml` is current and the schema has no warnings |
| 28 | repo root | `curl -fsS 'http://127.0.0.1:8480/api/v1/catalog/variants?sku=SIN-TOR-8X1'` | After row 25: the public SKU lookup through the proxy returns the default organization's published variant |
