"""Stable error codes, es-CR messages and API exception types (ADR 0001/0003).

Every API error body is the envelope ``{code, message, field_errors, request_id}``.
``code`` is a stable UPPER_SNAKE identifier; ``message`` is a fixed es-CR text
chosen by ``code`` (DRF/Django English or internal details are never echoed).
"""

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException

VALIDATION_ERROR = "VALIDATION_ERROR"
PARSE_ERROR = "PARSE_ERROR"
INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
INVALID_CURSOR = "INVALID_CURSOR"
INVALID_QUANTITY_INCREMENT = "INVALID_QUANTITY_INCREMENT"
NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
PERMISSION_DENIED = "PERMISSION_DENIED"
CSRF_FAILED = "CSRF_FAILED"
NOT_FOUND = "NOT_FOUND"
METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
NOT_ACCEPTABLE = "NOT_ACCEPTABLE"
UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
THROTTLED = "THROTTLED"
INTERNAL_ERROR = "INTERNAL_ERROR"
ERROR = "ERROR"

MESSAGES: dict[str, str] = {
    VALIDATION_ERROR: "Los datos enviados no son válidos.",
    PARSE_ERROR: "El cuerpo de la solicitud no es JSON válido.",
    INVALID_CREDENTIALS: "El correo electrónico o la contraseña no son correctos.",
    INVALID_CURSOR: "El cursor de paginación no es válido.",
    INVALID_QUANTITY_INCREMENT: (
        "La cantidad no es válida para este producto: debe ser múltiplo del incremento "
        "permitido y no menor que la cantidad mínima."
    ),
    NOT_AUTHENTICATED: "Debe iniciar sesión para realizar esta acción.",
    PERMISSION_DENIED: "No tiene permiso para realizar esta acción.",
    CSRF_FAILED: (
        "La verificación de seguridad (CSRF) falló. Recargue la página e intente de nuevo."
    ),
    NOT_FOUND: "El recurso solicitado no existe.",
    METHOD_NOT_ALLOWED: "El método HTTP no está permitido para este recurso.",
    NOT_ACCEPTABLE: "El formato de respuesta solicitado no está disponible.",
    UNSUPPORTED_MEDIA_TYPE: "El tipo de contenido de la solicitud no es compatible.",
    THROTTLED: "Demasiadas solicitudes. Espere un momento e intente de nuevo.",
    INTERNAL_ERROR: "Ocurrió un error interno. Intente de nuevo más tarde.",
    ERROR: "No se pudo completar la solicitud.",
}


def message_for(code: str) -> str:
    return MESSAGES.get(code, MESSAGES[ERROR])


class CodedAPIException(APIException):
    """APIException whose ``default_code`` is the public envelope code."""

    def __init__(self, detail: Any = None, code: str | None = None) -> None:
        resolved = code or str(self.default_code)
        super().__init__(detail=detail or message_for(resolved), code=resolved)


class CsrfFailed(CodedAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = CSRF_FAILED


class InvalidCredentials(CodedAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = INVALID_CREDENTIALS


class InvalidCursor(CodedAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = INVALID_CURSOR
