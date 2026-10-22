"""Catalog error codes.

``INVALID_QUANTITY_INCREMENT`` and its es-CR message live in ``common/errors.py``
with the other stable codes. The exception is both a ``CodedAPIException`` (so the
envelope ``code`` is ``INVALID_QUANTITY_INCREMENT``) and a ``ValidationError``
(so the shared handler fills ``field_errors``).
"""

from rest_framework import status
from rest_framework.exceptions import ErrorDetail, ValidationError

from common import errors

INVALID_QUANTITY_INCREMENT = errors.INVALID_QUANTITY_INCREMENT


class InvalidQuantityIncrement(errors.CodedAPIException, ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = INVALID_QUANTITY_INCREMENT

    def __init__(self, field: str, message: str) -> None:
        super().__init__(
            detail={field: [ErrorDetail(message, code=INVALID_QUANTITY_INCREMENT)]},
            code=INVALID_QUANTITY_INCREMENT,
        )
