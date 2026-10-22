"""Settings for pytest. Uses the same PostgreSQL configuration as base."""

import os
import secrets

# A random per-process key; nothing secret is committed.
os.environ.setdefault("DJANGO_SECRET_KEY", secrets.token_urlsafe(64))
# Static analysis (mypy) imports settings without a database; values are inert.
os.environ.setdefault("POSTGRES_HOST", "db")
os.environ.setdefault("POSTGRES_DB", "hardware_store")
os.environ.setdefault("POSTGRES_USER", "hardware_store")
os.environ.setdefault("POSTGRES_PASSWORD", "unused-unless-provided")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "testserver")

from .base import *  # noqa: F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
