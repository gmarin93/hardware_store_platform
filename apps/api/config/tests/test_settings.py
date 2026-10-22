import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from config.settings.base import validate_secret_key

API_DIR = Path(__file__).resolve().parents[2]
PLACEHOLDER = "change-me-local-only-placeholder-secret-key"
STRONG_KEY = "x" * 64


def _setup_django(**overrides: str) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("DJANGO_", "POSTGRES_"))
    }
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.base",
            "POSTGRES_HOST": "db",
            "POSTGRES_DB": "synthetic",
            "POSTGRES_USER": "synthetic",
            "POSTGRES_PASSWORD": "synthetic",
        }
    )
    env.update(overrides)
    return subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=API_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_refuses_placeholder_secret_key_with_debug_off() -> None:
    result = _setup_django(DJANGO_DEBUG="0", DJANGO_SECRET_KEY=PLACEHOLDER)

    assert result.returncode != 0
    assert "refusing to start with DEBUG off" in result.stderr


def test_refuses_missing_secret_key() -> None:
    result = _setup_django(DJANGO_DEBUG="1")

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY is required" in result.stderr


def test_debug_defaults_to_off() -> None:
    result = _setup_django(DJANGO_SECRET_KEY=PLACEHOLDER)

    assert result.returncode != 0
    assert "refusing to start with DEBUG off" in result.stderr


def test_starts_with_strong_key_and_debug_off() -> None:
    result = _setup_django(DJANGO_DEBUG="0", DJANGO_SECRET_KEY=STRONG_KEY)

    assert result.returncode == 0, result.stderr


def test_placeholder_allowed_only_with_debug_on() -> None:
    assert validate_secret_key(PLACEHOLDER, debug=True) == PLACEHOLDER
    with pytest.raises(ImproperlyConfigured):
        validate_secret_key("short-key", debug=False)


def test_locale_and_forwarded_header_defaults() -> None:
    assert settings.LANGUAGE_CODE == "es-cr"
    assert settings.TIME_ZONE == "America/Costa_Rica"
    assert settings.USE_TZ is True
    assert settings.USE_X_FORWARDED_HOST is False
    assert "django.contrib.admin" not in settings.INSTALLED_APPS
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
