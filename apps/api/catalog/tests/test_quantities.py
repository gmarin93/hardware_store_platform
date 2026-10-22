"""Quantity validation: exact multiples of the increment, never rounded."""

from decimal import Decimal
from typing import cast

import pytest
from rest_framework.exceptions import ErrorDetail, ValidationError

from catalog.errors import INVALID_QUANTITY_INCREMENT, InvalidQuantityIncrement
from catalog.models import Unit
from catalog.quantities import QuantityRule, validate_quantity, validate_variant_quantity
from catalog.tests.fixtures import CatalogWorld
from common.exceptions import api_exception_handler

PIECE = QuantityRule(Unit.PIECE, Decimal("1.000"), Decimal("1.000"))
PIECE_PAIRS = QuantityRule(Unit.PIECE, Decimal("2.000"), Decimal("2.000"))
KG_GRAM = QuantityRule(Unit.KG, Decimal("0.001"), Decimal("0.100"))
KG_QUARTER = QuantityRule(Unit.KG, Decimal("0.250"), Decimal("0.500"))
METER_HALF = QuantityRule(Unit.M, Decimal("0.500"), Decimal("1.000"))
CM_TEN = QuantityRule(Unit.CM, Decimal("10.000"), Decimal("50.000"))


def _code(exc: ValidationError, field: str = "quantity") -> str:
    detail = exc.detail
    assert isinstance(detail, dict)
    items = detail[field]
    assert isinstance(items, list)
    return str(cast(ErrorDetail, items[0]).code)


@pytest.mark.parametrize(
    ("rule", "raw", "expected"),
    [
        (PIECE, "1", "1.000"),
        (PIECE, "25", "25.000"),
        (PIECE, "3.000", "3.000"),
        (PIECE, "3.0000000", "3.000"),  # same value; trailing zeros are not rounding
        (PIECE_PAIRS, "4", "4.000"),
        (KG_GRAM, "0.1", "0.100"),
        (KG_GRAM, "0.101", "0.101"),
        (KG_GRAM, "2.345", "2.345"),
        (KG_GRAM, "99999999999.999", "99999999999.999"),  # NUMERIC(14,3) maximum
        (KG_QUARTER, "0.5", "0.500"),
        (KG_QUARTER, "0.75", "0.750"),
        (METER_HALF, "1", "1.000"),
        (METER_HALF, "1.5", "1.500"),
        (CM_TEN, "50", "50.000"),
        (CM_TEN, "120", "120.000"),
    ],
)
def test_valid_quantities_are_returned_exactly(rule: QuantityRule, raw: str, expected: str) -> None:
    value = validate_quantity(rule, raw)
    assert value == Decimal(expected)
    assert str(value) == expected


@pytest.mark.parametrize(
    ("rule", "raw"),
    [
        (PIECE, "1.5"),  # pieces are whole
        (PIECE, "0"),  # below minimum
        (PIECE, "0.999"),
        (PIECE, "1.001"),
        (PIECE_PAIRS, "3"),  # not a multiple of 2
        (PIECE_PAIRS, "0"),
        (KG_GRAM, "0.099"),  # boundary: one gram below the minimum
        (KG_GRAM, "0.1005"),  # half a gram: rejected, never rounded to 0.100/0.101
        (KG_GRAM, "1.0001"),
        (KG_GRAM, "0.000"),
        (KG_QUARTER, "0.25"),  # multiple but below the minimum
        (KG_QUARTER, "0.6"),
        (KG_QUARTER, "0.7500001"),
        (METER_HALF, "1.25"),
        (METER_HALF, "0.5"),
        (CM_TEN, "55"),
        (CM_TEN, "40"),
    ],
)
def test_non_multiples_and_values_below_minimum_are_rejected(rule: QuantityRule, raw: str) -> None:
    with pytest.raises(InvalidQuantityIncrement) as excinfo:
        validate_quantity(rule, raw)
    assert _code(excinfo.value) == INVALID_QUANTITY_INCREMENT


@pytest.mark.parametrize(
    "raw",
    [
        1,
        1.5,
        Decimal(1),
        None,
        "",
        " 1",
        "1 ",
        "1,5",
        "-1",
        "+1",
        "1e3",
        ".5",
        "1.",
        "abc",
        "\uff11",
    ],
)
def test_malformed_quantities_are_validation_errors(raw: object) -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_quantity(PIECE, raw)
    assert not isinstance(excinfo.value, InvalidQuantityIncrement)
    assert _code(excinfo.value) == "invalid"


def test_too_large_quantity_is_validation_error() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_quantity(KG_GRAM, "100000000000")
    assert not isinstance(excinfo.value, InvalidQuantityIncrement)
    assert _code(excinfo.value) == "max_value"


def test_invalid_quantity_renders_400_envelope_in_spanish() -> None:
    with pytest.raises(InvalidQuantityIncrement) as excinfo:
        validate_quantity(KG_QUARTER, "0.6", field="lines.0.quantity")
    response = api_exception_handler(excinfo.value, {})
    assert response.status_code == 400
    data = response.data
    assert data["code"] == INVALID_QUANTITY_INCREMENT
    assert data["message"].startswith("La cantidad no es válida")
    assert data["field_errors"] == {
        "lines.0.quantity": [
            {
                "code": INVALID_QUANTITY_INCREMENT,
                "message": "La cantidad debe ser múltiplo de 0.25 kilogramo y al menos "
                "0.5 kilogramo.",
            }
        ]
    }


@pytest.mark.django_db
def test_variant_rule_comes_from_the_variant(catalog: CatalogWorld) -> None:
    assert validate_variant_quantity(catalog.variant_b, "1.5") == Decimal("1.500")
    with pytest.raises(InvalidQuantityIncrement):
        validate_variant_quantity(catalog.variant_b, "1.25")
    with pytest.raises(InvalidQuantityIncrement):
        validate_variant_quantity(catalog.variant, "1.5")
