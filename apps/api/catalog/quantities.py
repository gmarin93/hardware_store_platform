"""Quantity validation for a variant's sales unit (ADR 0001: never rounds).

Input is a plain decimal string (``"2"``, ``"0.125"``); no sign, exponent,
whitespace, thousands separator or comma decimal mark. The value is accepted
only when it is an exact multiple of ``quantity_increment`` and not below
``min_quantity``; anything else is ``400 INVALID_QUANTITY_INCREMENT``. Values are
compared exactly with ``Decimal`` arithmetic, so ``"1.0005"`` with increment
``0.001`` is rejected rather than rounded to ``1.001``/``1.000``.

Malformed strings (or non-strings) are ``400 VALIDATION_ERROR``. Accepted values
are returned at NUMERIC(14,3) scale (exact, because every multiple of a
3-decimal increment has at most 3 decimals).
"""

import re
from dataclasses import dataclass
from decimal import Context, Decimal, localcontext

from rest_framework.exceptions import ErrorDetail, ValidationError

from catalog.errors import InvalidQuantityIncrement
from catalog.models import QUANTITY_DECIMAL_PLACES, QUANTITY_MAX_DIGITS, Unit, Variant

_DECIMAL_STRING = re.compile(r"\A[0-9]{1,32}(?:\.[0-9]{1,32})?\Z")
_SCALE = Decimal(1).scaleb(-QUANTITY_DECIMAL_PLACES)
_MAX_INTEGER_DIGITS = QUANTITY_MAX_DIGITS - QUANTITY_DECIMAL_PLACES
# Wide enough that every operation on accepted input (<= 65 digits) is exact.
_EXACT = Context(prec=100)


@dataclass(frozen=True)
class QuantityRule:
    unit: str
    increment: Decimal
    min_quantity: Decimal

    @classmethod
    def for_variant(cls, variant: Variant) -> "QuantityRule":
        return cls(variant.sales_unit, variant.quantity_increment, variant.min_quantity)


def _unit_label(unit: str) -> str:
    return Unit(unit).label if unit in Unit.values else unit


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def parse_quantity(raw: object, field: str = "quantity") -> Decimal:
    """Parse a decimal string exactly; malformed input is VALIDATION_ERROR."""
    if not isinstance(raw, str) or not _DECIMAL_STRING.match(raw):
        raise ValidationError(
            {
                field: [
                    ErrorDetail(
                        'Indique la cantidad como número decimal en texto, p. ej. "2.5".',
                        code="invalid",
                    )
                ]
            }
        )
    value = Decimal(raw)
    if value.adjusted() >= _MAX_INTEGER_DIGITS:
        raise ValidationError(
            {field: [ErrorDetail("La cantidad es demasiado grande.", code="max_value")]}
        )
    return value


def validate_quantity(rule: QuantityRule, raw: object, field: str = "quantity") -> Decimal:
    """Return the exact quantity or raise (never rounds)."""
    value = parse_quantity(raw, field)
    with localcontext(_EXACT):
        is_multiple = value % rule.increment == 0
    if value < rule.min_quantity or not is_multiple:
        unit = _unit_label(rule.unit)
        raise InvalidQuantityIncrement(
            field,
            f"La cantidad debe ser múltiplo de {_plain(rule.increment)} {unit} y al menos "
            f"{_plain(rule.min_quantity)} {unit}.",
        )
    return value.quantize(_SCALE)


def validate_variant_quantity(variant: Variant, raw: object, field: str = "quantity") -> Decimal:
    return validate_quantity(QuantityRule.for_variant(variant), raw, field)
