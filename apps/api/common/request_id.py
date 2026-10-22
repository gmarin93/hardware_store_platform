"""Request correlation ID (ADR 0001/0003).

A valid inbound ``X-Request-ID`` (1-64 chars of ``[A-Za-z0-9._:-]`` starting
with an alphanumeric) is reused; anything else is replaced by a generated
UUIDv4. The value is stored on the request, echoed as a response header,
placed in every error envelope and exposed to log records as ``request_id``.
"""

import logging
import re
import uuid
from collections.abc import Callable
from contextvars import ContextVar

from django.http import HttpRequest, HttpResponseBase

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_META_KEY = "HTTP_X_REQUEST_ID"
REQUEST_ID_ATTR = "request_id"
_VALID_REQUEST_ID = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:\-]{0,63}\Z")

_current_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def is_valid_request_id(value: str) -> bool:
    return bool(_VALID_REQUEST_ID.match(value))


def get_request_id(request: HttpRequest | None) -> str:
    """Return the request's correlation ID, assigning one if missing."""
    if request is None:
        return str(uuid.uuid4())
    existing = getattr(request, REQUEST_ID_ATTR, None)
    if isinstance(existing, str):
        return existing
    inbound = request.META.get(REQUEST_ID_META_KEY, "")
    request_id = inbound if isinstance(inbound, str) and is_valid_request_id(inbound) else ""
    request_id = request_id or str(uuid.uuid4())
    setattr(request, REQUEST_ID_ATTR, request_id)
    return request_id


class RequestIDMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        request_id = get_request_id(request)
        token = _current_request_id.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _current_request_id.reset(token)
        response[REQUEST_ID_HEADER] = request_id
        return response


class RequestIDLogFilter(logging.Filter):
    """Adds ``record.request_id`` so formatters can include it."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, REQUEST_ID_ATTR):
            # django.request logs after the middleware chain returns, but
            # attaches the request to the record.
            request = getattr(record, "request", None)
            from_request = getattr(request, REQUEST_ID_ATTR, None)
            record.request_id = (
                from_request if isinstance(from_request, str) else _current_request_id.get()
            )
        return True
