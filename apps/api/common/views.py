"""Envelope responses for requests that never reach a DRF view."""

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from common import errors
from common.exceptions import envelope_json_response


@csrf_exempt  # nothing is mutated; keeps unknown-path responses uniform
def api_not_found(request: HttpRequest, *args: object, **kwargs: object) -> JsonResponse:
    """Catch-all for unknown ``/api/v1/`` paths; identical body to a DRF 404."""
    return envelope_json_response(request, errors.NOT_FOUND, 404)


def handler404(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return envelope_json_response(request, errors.NOT_FOUND, 404)


def handler500(request: HttpRequest) -> JsonResponse:
    return envelope_json_response(request, errors.INTERNAL_ERROR, 500)


def csrf_failure(request: HttpRequest, reason: str = "") -> JsonResponse:
    """CSRF_FAILURE_VIEW for non-DRF views; the reason is never echoed."""
    return envelope_json_response(request, errors.CSRF_FAILED, 403)
