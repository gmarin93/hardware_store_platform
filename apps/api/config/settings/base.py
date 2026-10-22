"""Environment-driven Django settings shared by every environment.

All runtime values come from environment variables (see the repository
``.env.example``). Startup fails fast when a secure value is missing.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Values shipped in .env.example. They must never be used with DEBUG off.
SECRET_KEY_PLACEHOLDERS = frozenset({"change-me-local-only-placeholder-secret-key"})
SECRET_KEY_MIN_LENGTH = 50


def env_str(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise ImproperlyConfigured(f"Environment variable {name} is required.")
    return value


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(f"Environment variable {name} must be a boolean.")


def env_list(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def validate_secret_key(secret_key: str, *, debug: bool) -> str:
    """Refuse placeholder or weak keys whenever DEBUG is off."""
    if not secret_key:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required.")
    if not debug and (
        secret_key in SECRET_KEY_PLACEHOLDERS
        or secret_key.startswith("change-me")
        or len(secret_key) < SECRET_KEY_MIN_LENGTH
    ):
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is a placeholder or too short; refusing to start with DEBUG off."
        )
    return secret_key


# Secure default: DEBUG is off unless explicitly enabled for local work.
DEBUG = env_bool("DJANGO_DEBUG", default=False)
SECRET_KEY = validate_secret_key(os.environ.get("DJANGO_SECRET_KEY", ""), debug=DEBUG)

# Explicit host and origin allowlists; no wildcards are added implicitly.
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Forwarded headers (ADR 0001): Django is reachable only through the proxy on
# the internal Compose network, and the proxy overwrites X-Forwarded-*.
# X-Forwarded-Host/Port are never trusted. The proto header is trusted only
# when explicitly enabled for a deployment that terminates TLS at the proxy.
USE_X_FORWARDED_HOST = False
USE_X_FORWARDED_PORT = False
if env_bool("DJANGO_TRUST_PROXY_PROTO_HEADER", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "drf_spectacular",
    # Project apps. P1-02B adds "catalog" below this line.
    "accounts",
    "organizations",
    "catalog",
]

# Custom user (UUID pk, email login). Must exist before the first migration.
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Single-organization MVP: guests resolve this organization (ADR 0001).
DEFAULT_ORGANIZATION_SLUG = os.environ.get("DJANGO_DEFAULT_ORGANIZATION_SLUG", "") or "demo"

# Peers whose X-Forwarded-For is trusted for client-address throttling: IPs,
# CIDRs or hostnames (resolved, cached 60 s). Default: the Compose proxy service.
TRUSTED_PROXY_HOSTS = env_list("DJANGO_TRUSTED_PROXY_HOSTS") or ["proxy"]

MIDDLEWARE = [
    # Outermost: sees the final response (incl. Set-Cookie) for cache headers.
    "common.cache_headers.SessionCacheHeadersMiddleware",
    "common.request_id.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": env_str("POSTGRES_HOST"),
        "PORT": env_str("POSTGRES_PORT", "5432"),
        "NAME": env_str("POSTGRES_DB"),
        "USER": env_str("POSTGRES_USER"),
        "PASSWORD": env_str("POSTGRES_PASSWORD"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": 5},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sessions and CSRF (ADR 0001): DB-backed sessions; Secure cookies outside local.
SECURE_COOKIES = env_bool("DJANGO_SECURE_COOKIES", default=not DEBUG)
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_HTTPONLY = False  # read by the web client and sent as X-CSRFToken
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = SECURE_COOKIES
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"
CSRF_FAILURE_VIEW = "common.views.csrf_failure"

# Per-process cache; used only for login throttling in P1 (ADR 0003).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

LANGUAGE_CODE = "es-cr"
LANGUAGES = [("es-cr", "Español (Costa Rica)")]
TIME_ZONE = "America/Costa_Rica"
USE_I18N = True
USE_TZ = True

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["common.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.CursorPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {"login_ip": "20/min", "login_account": "5/min"},
    # DRF's own XFF parsing is disabled; login throttles use common.client_ip,
    # which trusts X-Forwarded-For only from TRUSTED_PROXY_HOSTS.
    "NUM_PROXIES": 0,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Hardware Store Platform API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Never log cookies, CSRF tokens or passwords (ADR 0001). Application loggers
# log ids only; Django's request loggers log method and path, not headers.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "common.request_id.RequestIDLogFilter"},
        "sensitive": {"()": "common.log_filters.SensitiveRecordFilter"},
    },
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"}
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_id"],
            "formatter": "default",
        }
    },
    "loggers": {
        # Drop Django's default "django" handlers so records are emitted once (via root).
        "django": {"handlers": [], "propagate": True},
        # SQL with parameters (password hashes, session data) is logged at DEBUG
        # when settings.DEBUG is on; never let it through.
        "django.db.backends": {"level": "WARNING", "handlers": [], "propagate": True},
        "django.security.csrf": {"filters": ["sensitive"], "handlers": [], "propagate": True},
        "django.request": {"filters": ["sensitive"], "handlers": [], "propagate": True},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
}
