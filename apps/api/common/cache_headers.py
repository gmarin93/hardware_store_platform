"""Cache headers for session-bearing responses (ADR 0001).

Placed first in MIDDLEWARE so it sees the final response, including
``Set-Cookie`` added by the session and CSRF middleware. Every response gets
``Vary: Cookie``. ``Cache-Control: private, no-store`` is forced when the user
is authenticated, the request carried a session cookie, or the response sets
any cookie (login, logout, CSRF bootstrap).
"""

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponseBase
from django.utils.cache import patch_vary_headers

NO_STORE = "private, no-store"


def _is_session_bound(request: HttpRequest, response: HttpResponseBase) -> bool:
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return True
    if settings.SESSION_COOKIE_NAME in request.COOKIES:
        return True
    return bool(response.cookies)


class SessionCacheHeadersMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        response = self.get_response(request)
        patch_vary_headers(response, ("Cookie",))
        if _is_session_bound(request, response):
            response["Cache-Control"] = NO_STORE
        return response
