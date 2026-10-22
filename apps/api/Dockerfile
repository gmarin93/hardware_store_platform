# syntax=docker/dockerfile:1
# Local API image. Build context: apps/api. Images pinned by tag and digest (ADR 0002).
FROM ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa AS uv

FROM python:3.13.17-slim-trixie@sha256:19ed48e5e9c132082510ba9efb11bc2098d582f610374670fa30b6b17026617b AS base
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH
WORKDIR /app
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app
COPY pyproject.toml uv.lock ./

# Runtime dependencies only.
FROM base AS runtime
RUN uv sync --locked --no-dev --no-install-project
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-"]

# Local development and checks: includes the dev dependency group (pytest, ruff, mypy).
FROM base AS dev
RUN uv sync --locked --no-install-project
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--reload", "--access-logfile", "-"]
