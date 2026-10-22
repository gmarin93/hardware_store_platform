"""Opaque keyset cursor pagination (ADR 0001/0003).

Response: ``{results, next_cursor, previous_cursor}``. Query parameters:
``cursor`` (opaque, signed) and ``page_size`` (default 20, max 100; larger
values are clamped, non-integers or values < 1 are a VALIDATION_ERROR).

The ordering is a tuple of direct, non-null model attributes that must end with
``id`` (or ``-id``), so every position is unique and pages never skip or repeat
rows. Views set ``cursor_ordering``; the default is ``("-created_at", "-id")``.
The cursor stores the ordering values of the boundary row, signed with
``django.core.signing`` so it is opaque and tamper-evident. It carries no
authorization: rows always come from the view's already-scoped queryset.
"""

from collections.abc import Sequence
from typing import Any

from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Model, Q, QuerySet
from rest_framework import exceptions
from rest_framework.pagination import BasePagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import InvalidCursor

CURSOR_SALT = "common.pagination.cursor"
_NEXT = "n"
_PREVIOUS = "p"


def _split(field: str) -> tuple[str, bool]:
    """Return (attribute, descending)."""
    return (field[1:], True) if field.startswith("-") else (field, False)


def validate_ordering(ordering: Sequence[str]) -> tuple[str, ...]:
    ordering = tuple(ordering)
    if not ordering or _split(ordering[-1])[0] != "id":
        raise ValueError("Cursor ordering must end with 'id' or '-id'.")
    for field in ordering:
        if "__" in _split(field)[0]:
            raise ValueError("Cursor ordering supports direct model attributes only.")
    return ordering


def _reverse(ordering: Sequence[str]) -> tuple[str, ...]:
    return tuple(f[1:] if f.startswith("-") else f"-{f}" for f in ordering)


def _after(ordering: Sequence[str], values: Sequence[Any]) -> Q:
    """Rows strictly after ``values`` in ``ordering`` (lexicographic keyset)."""
    condition = Q()
    for index, field in enumerate(ordering):
        name, descending = _split(field)
        lookup = "lt" if descending else "gt"
        clause = Q(**{f"{name}__{lookup}": values[index]})
        for prior_field, prior_value in zip(ordering[:index], values[:index], strict=True):
            clause &= Q(**{_split(prior_field)[0]: prior_value})
        condition |= clause
    return condition


class CursorPagination(BasePagination):
    page_size = 20
    max_page_size = 100
    cursor_query_param = "cursor"
    page_size_query_param = "page_size"
    default_ordering: tuple[str, ...] = ("-created_at", "-id")

    def __init__(self) -> None:
        self.next_cursor: str | None = None
        self.previous_cursor: str | None = None

    def get_ordering(self, view: APIView | None) -> tuple[str, ...]:
        ordering = getattr(view, "cursor_ordering", None) or self.default_ordering
        return validate_ordering(ordering)

    def get_page_size(self, request: Request) -> int:
        raw = request.query_params.get(self.page_size_query_param)
        if raw is None or raw == "":
            return self.page_size
        try:
            value = int(raw)
        except ValueError:
            value = 0
        if value < 1:
            raise exceptions.ValidationError(
                {
                    self.page_size_query_param: [
                        exceptions.ErrorDetail(
                            f"Debe ser un número entero entre 1 y {self.max_page_size}.",
                            code="invalid",
                        )
                    ]
                }
            )
        return min(value, self.max_page_size)

    def encode_cursor(self, values: Sequence[Any], direction: str) -> str:
        return signing.dumps(
            {"v": [str(v) for v in values], "d": direction}, salt=CURSOR_SALT, compress=False
        )

    def decode_cursor(self, raw: str, size: int) -> tuple[list[str], str]:
        try:
            payload = signing.loads(raw, salt=CURSOR_SALT)
        except signing.BadSignature as exc:
            raise InvalidCursor() from exc
        if not isinstance(payload, dict):
            raise InvalidCursor()
        values, direction = payload.get("v"), payload.get("d")
        if (
            direction not in (_NEXT, _PREVIOUS)
            or not isinstance(values, list)
            or len(values) != size
            or not all(isinstance(v, str) for v in values)
        ):
            raise InvalidCursor()
        return values, direction

    def _values(self, obj: Model, ordering: Sequence[str]) -> list[Any]:
        return [getattr(obj, _split(field)[0]) for field in ordering]

    def paginate_queryset(
        self,
        queryset: QuerySet[Any, Any] | Sequence[Any],
        request: Request,
        view: APIView | None = None,
    ) -> list[Any]:
        if not isinstance(queryset, QuerySet):
            raise TypeError("CursorPagination requires a QuerySet.")
        ordering = self.get_ordering(view)
        size = self.get_page_size(request)
        raw_cursor = request.query_params.get(self.cursor_query_param)

        if not raw_cursor:
            rows = list(queryset.order_by(*ordering)[: size + 1])
            has_more = len(rows) > size
            rows = rows[:size]
            self.previous_cursor = None
            self.next_cursor = (
                self.encode_cursor(self._values(rows[-1], ordering), _NEXT) if has_more else None
            )
            return rows

        values, direction = self.decode_cursor(raw_cursor, len(ordering))
        try:
            if direction == _NEXT:
                filtered = queryset.filter(_after(ordering, values)).order_by(*ordering)
                rows = list(filtered[: size + 1])
            else:
                reverse = _reverse(ordering)
                filtered = queryset.filter(_after(reverse, values)).order_by(*reverse)
                rows = list(filtered[: size + 1])
        except (ValueError, TypeError, DjangoValidationError) as exc:
            # A signed but stale/incompatible cursor (e.g. ordering changed).
            raise InvalidCursor() from exc

        has_more = len(rows) > size
        rows = rows[:size]
        if direction == _PREVIOUS:
            rows.reverse()
            self.previous_cursor = (
                self.encode_cursor(self._values(rows[0], ordering), _PREVIOUS) if has_more else None
            )
            self.next_cursor = (
                self.encode_cursor(self._values(rows[-1], ordering), _NEXT) if rows else None
            )
        else:
            self.next_cursor = (
                self.encode_cursor(self._values(rows[-1], ordering), _NEXT) if has_more else None
            )
            self.previous_cursor = (
                self.encode_cursor(self._values(rows[0], ordering), _PREVIOUS) if rows else None
            )
        return rows

    def get_paginated_response(self, data: Any) -> Response:
        return Response(
            {
                "results": data,
                "next_cursor": self.next_cursor,
                "previous_cursor": self.previous_cursor,
            }
        )

    def get_paginated_response_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["results", "next_cursor", "previous_cursor"],
            "properties": {
                "results": schema,
                "next_cursor": {"type": "string", "nullable": True},
                "previous_cursor": {"type": "string", "nullable": True},
            },
        }

    def get_schema_operation_parameters(self, view: APIView) -> list[dict[str, Any]]:
        return [
            {
                "name": self.cursor_query_param,
                "required": False,
                "in": "query",
                "description": "Cursor opaco devuelto como next_cursor o previous_cursor.",
                "schema": {"type": "string"},
            },
            {
                "name": self.page_size_query_param,
                "required": False,
                "in": "query",
                "description": f"Tamaño de página (1-{self.max_page_size}, por defecto "
                f"{self.page_size}).",
                "schema": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": self.max_page_size,
                    "default": self.page_size,
                },
            },
        ]
