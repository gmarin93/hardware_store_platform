"""DRF exception handler producing the uniform error envelope (ADR 0001/0003)."""

import logging
from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404, HttpRequest, JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

from common import errors
from common.request_id import get_request_id

logger = logging.getLogger(__name__)

FieldErrors = dict[str, list[dict[str, str]]]


def build_envelope(
    code: str, request_id: str, field_errors: FieldErrors | None = None
) -> dict[str, Any]:
    return {
        "code": code,
        "message": errors.message_for(code),
        "field_errors": field_errors or {},
        "request_id": request_id,
    }


def envelope_json_response(
    request: HttpRequest | None, code: str, status_code: int
) -> JsonResponse:
    """Envelope for non-DRF responses (URL resolver 404, 500 handler)."""
    body = build_envelope(code, get_request_id(request))
    return JsonResponse(
        body,
        status=status_code,
        json_dumps_params={"ensure_ascii": False, "separators": (",", ":")},
    )


def _error_item(detail: exceptions.ErrorDetail | str) -> dict[str, str]:
    code = getattr(detail, "code", None) or "invalid"
    return {"code": str(code), "message": str(detail)}


def _merge(target: FieldErrors, key: str, items: list[dict[str, str]]) -> None:
    if items:
        target.setdefault(key, []).extend(items)


def flatten_field_errors(detail: Any, prefix: str = "") -> FieldErrors:
    """Flatten DRF validation detail into ``{field: [{code, message}]}``.

    Nested serializers use dotted paths (``lines.0.quantity``); errors that
    are not tied to a field use DRF's ``non_field_errors`` key.
    """
    result: FieldErrors = {}
    own_key = prefix or api_settings.NON_FIELD_ERRORS_KEY
    if isinstance(detail, Mapping):
        for key, value in detail.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            for k, v in flatten_field_errors(value, child).items():
                _merge(result, k, v)
    elif isinstance(detail, list):
        for index, item in enumerate(detail):
            if isinstance(item, Mapping | list):
                child = f"{prefix}.{index}" if prefix else str(index)
                for k, v in flatten_field_errors(item, child).items():
                    _merge(result, k, v)
            else:
                _merge(result, own_key, [_error_item(item)])
    else:
        _merge(result, own_key, [_error_item(detail)])
    return result


def _code_for(exc: exceptions.APIException) -> str:
    if isinstance(exc, errors.CodedAPIException):
        return str(exc.default_code)
    if isinstance(exc, exceptions.ValidationError):
        return errors.VALIDATION_ERROR
    if isinstance(exc, exceptions.ParseError):
        return errors.PARSE_ERROR
    if isinstance(exc, exceptions.NotAuthenticated | exceptions.AuthenticationFailed):
        return errors.NOT_AUTHENTICATED
    if isinstance(exc, exceptions.PermissionDenied):
        return errors.PERMISSION_DENIED
    if isinstance(exc, exceptions.NotFound):
        return errors.NOT_FOUND
    if isinstance(exc, exceptions.MethodNotAllowed):
        return errors.METHOD_NOT_ALLOWED
    if isinstance(exc, exceptions.NotAcceptable):
        return errors.NOT_ACCEPTABLE
    if isinstance(exc, exceptions.UnsupportedMediaType):
        return errors.UNSUPPORTED_MEDIA_TYPE
    if isinstance(exc, exceptions.Throttled):
        return errors.THROTTLED
    return str(exc.default_code).upper() if exc.default_code else errors.ERROR


def api_exception_handler(exc: Exception, context: Mapping[str, Any]) -> Response:
    """REST_FRAMEWORK['EXCEPTION_HANDLER'].

    Delegates to DRF for status and headers (WWW-Authenticate, Retry-After),
    then replaces the body with the envelope. Unexpected exceptions become a
    500 INTERNAL_ERROR envelope after marking the transaction for rollback;
    only the exception class, view and request id are logged.
    """
    view = context.get("view")
    request = getattr(context.get("request"), "_request", None)
    request_id = get_request_id(request)

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, dict(context))
    if response is None or not isinstance(exc, exceptions.APIException):
        # Mark an ATOMIC_REQUESTS transaction for rollback, as DRF's handler
        # does for handled errors; a 500 must never commit a partial write.
        set_rollback()
        # Class, view and request id only: exception messages and tracebacks
        # can carry personal data. Tracebacks are emitted only with DEBUG on.
        logger.error(
            "Unhandled API exception %s in %s (request %s)",
            type(exc).__name__,
            type(view).__name__ if view is not None else "-",
            request_id,
        )
        if settings.DEBUG:
            logger.debug("Traceback for request %s", request_id, exc_info=exc)
        return Response(
            build_envelope(errors.INTERNAL_ERROR, request_id),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = _code_for(exc)
    field_errors: FieldErrors = {}
    if isinstance(exc, exceptions.ValidationError):
        field_errors = flatten_field_errors(exc.detail)
    response.data = build_envelope(code, request_id, field_errors)
    return response
