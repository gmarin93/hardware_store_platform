"""OpenAPI components for the error envelope (drf-spectacular)."""

from typing import Any

from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers


class SessionCookieScheme(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    """Documents ``common.authentication.SessionAuthentication`` (session cookie)."""

    target_class = "common.authentication.SessionAuthentication"
    name = "cookieAuth"

    def get_security_definition(self, auto_schema: Any) -> dict[str, str]:
        return {"type": "apiKey", "in": "cookie", "name": settings.SESSION_COOKIE_NAME}


class FieldErrorSerializer(serializers.Serializer[object]):
    code = serializers.CharField()
    message = serializers.CharField()


class ErrorEnvelopeSerializer(serializers.Serializer[object]):
    code = serializers.CharField(help_text="Código estable UPPER_SNAKE.")
    message = serializers.CharField(help_text="Mensaje en español (es-CR).")
    field_errors = serializers.DictField(
        child=FieldErrorSerializer(many=True),
        help_text="Errores por campo (ruta con puntos) o {}.",
    )
    request_id = serializers.CharField()


_DESCRIPTIONS = {
    400: "VALIDATION_ERROR, PARSE_ERROR, INVALID_CREDENTIALS o INVALID_CURSOR",
    401: "NOT_AUTHENTICATED",
    403: "PERMISSION_DENIED o CSRF_FAILED",
    404: "NOT_FOUND (también fuera de alcance)",
    405: "METHOD_NOT_ALLOWED",
    429: "THROTTLED",
}


def error_responses(*status_codes: int) -> dict[int, OpenApiResponse]:
    """``extend_schema(responses={..., **error_responses(401, 404)})``."""
    return {
        code: OpenApiResponse(response=ErrorEnvelopeSerializer, description=_DESCRIPTIONS[code])
        for code in status_codes
    }
