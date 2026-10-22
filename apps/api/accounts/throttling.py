"""Login throttling (ADR 0001/0003).

Two independent limits; every login attempt counts (success or failure):
* ``login_ip``: per client address from ``common.client_ip.client_ip``:
  ``X-Forwarded-For`` is used only when the peer is a trusted proxy
  (``TRUSTED_PROXY_HOSTS``), otherwise ``REMOTE_ADDR``.
* ``login_account``: per normalized email, keyed by a SHA-256 digest so the
  address is not stored in cache keys.

The cache is per process (LocMem) in P1; with N gunicorn workers the effective
limit is up to N times the configured rate. A shared cache is a later change.
"""

import hashlib

from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from accounts.models import normalize_email
from common.client_ip import client_ip


class LoginIPThrottle(SimpleRateThrottle):
    scope = "login_ip"

    def get_ident(self, request: Request) -> str:
        return client_ip(request._request)

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class LoginAccountThrottle(SimpleRateThrottle):
    scope = "login_account"

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        data = request.data
        email = data.get("email") if isinstance(data, dict) else None
        if not isinstance(email, str) or not email.strip():
            return None
        digest = hashlib.sha256(normalize_email(email).encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}
