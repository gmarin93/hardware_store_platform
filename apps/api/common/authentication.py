"""Session authentication with 401 semantics and CSRF_FAILED errors (ADR 0003).

* DRF's ``SessionAuthentication`` has no ``WWW-Authenticate`` value, so DRF
  turns NotAuthenticated into 403. Returning ``Session`` makes unauthenticated
  requests 401 NOT_AUTHENTICATED (no browser credential prompt is triggered).
* DRF enforces CSRF only for already-authenticated sessions. Login and logout
  must enforce it for anonymous requests too: views use ``EnforceCsrfMixin``.
"""

from typing import Any

from django.http import HttpRequest, HttpResponse, QueryDict
from django.utils.datastructures import MultiValueDict
from rest_framework import authentication
from rest_framework.request import Request

from common.errors import CsrfFailed

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _no_response(request: HttpRequest) -> HttpResponse:  # pragma: no cover - never called
    return HttpResponse()


def enforce_csrf(request: HttpRequest) -> None:
    """Run Django's CSRF checks (token and Origin/Referer); raise CsrfFailed.

    The failure reason is not exposed to the client or logged with values.
    """
    if not hasattr(request, "_post"):
        # The token is accepted only from the X-CSRFToken header. Pre-empt
        # Django's form parsing so the body stream is left for DRF's parsers
        # (otherwise form/multipart bodies are consumed here and a JSON-only
        # endpoint silently sees empty data instead of answering 415).
        request._post = QueryDict()  # type: ignore[attr-defined]
        request._files = MultiValueDict()  # type: ignore[attr-defined]
    check = authentication.CSRFCheck(_no_response)
    check.process_request(request)
    reason = check.process_view(request, _no_response, (), {})
    if reason:
        raise CsrfFailed()


class SessionAuthentication(authentication.SessionAuthentication):
    def authenticate_header(self, request: Request) -> str:
        return "Session"

    def enforce_csrf(self, request: Request) -> None:
        enforce_csrf(request._request)


class EnforceCsrfMixin:
    """Enforce CSRF on unsafe methods before authentication and throttling.

    For views reachable anonymously that change session state (login/logout).
    """

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        if request.method not in SAFE_METHODS:
            enforce_csrf(request._request)
        super().initial(request, *args, **kwargs)  # type: ignore[misc]
