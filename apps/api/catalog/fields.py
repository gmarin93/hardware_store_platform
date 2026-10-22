"""Read-only serializer fields with explicitly named OpenAPI enum components.

drf-spectacular derives enum component names from property names; ``status``
(catalog vs. media) and ``sales_unit``/``stock_unit`` would collide or get
several names and fail ``--fail-on-warn``. Each field class below maps to one
named component instead (``CatalogStatus``, ``MediaStatus``, ``Unit``,
``AttributeValueType``, ``AttributeUnit``).
"""

from decimal import Decimal
from typing import Any

from django.db import models
from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from catalog.models import (
    AttributeUnit,
    AttributeValue,
    AttributeValueType,
    CatalogStatus,
    MediaStatus,
    Unit,
)


class _EnumField(serializers.ChoiceField):
    enum: type[models.TextChoices]

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("read_only", True)
        super().__init__(choices=[v for v in self.enum.values if v], **kwargs)


class CatalogStatusField(_EnumField):
    enum = CatalogStatus


class MediaStatusField(_EnumField):
    enum = MediaStatus


class UnitField(_EnumField):
    enum = Unit


class AttributeValueTypeField(_EnumField):
    enum = AttributeValueType


class AttributeUnitField(_EnumField):
    """``null`` when the attribute has no unit."""

    enum = AttributeUnit

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("allow_null", True)
        super().__init__(**kwargs)

    def to_representation(self, value: Any) -> Any:
        return value or None


class _EnumFieldExtension(OpenApiSerializerFieldExtension):  # type: ignore[no-untyped-call]
    component: str
    enum: type[models.TextChoices]

    def get_name(self) -> str:
        return self.component

    def map_serializer_field(self, auto_schema: Any, direction: Any) -> dict[str, Any]:
        values = [v for v in self.enum.values if v]
        labels = "\n".join(f"* `{v}` - {self.enum(v).label}" for v in values)
        return {"type": "string", "enum": values, "description": labels}


class CatalogStatusExtension(_EnumFieldExtension):  # type: ignore[no-untyped-call]
    target_class = CatalogStatusField
    component = "CatalogStatus"
    enum = CatalogStatus


class MediaStatusExtension(_EnumFieldExtension):  # type: ignore[no-untyped-call]
    target_class = MediaStatusField
    component = "MediaStatus"
    enum = MediaStatus


class UnitExtension(_EnumFieldExtension):  # type: ignore[no-untyped-call]
    target_class = UnitField
    component = "Unit"
    enum = Unit


class AttributeValueTypeExtension(_EnumFieldExtension):  # type: ignore[no-untyped-call]
    target_class = AttributeValueTypeField
    component = "AttributeValueType"
    enum = AttributeValueType


class AttributeUnitExtension(_EnumFieldExtension):  # type: ignore[no-untyped-call]
    target_class = AttributeUnitField
    component = "AttributeUnit"
    enum = AttributeUnit


def format_decimal(value: Decimal) -> str:
    """Plain decimal string without exponent or trailing zeros (``"0.5"``, ``"600"``)."""
    text = format(value.normalize(), "f")
    return "0" if text in {"-0", ""} else text


@extend_schema_field(
    {
        "type": "string",
        "description": 'Valor como texto: decimal ("12.7"), texto libre o "true"/"false" '
        "según value_type.",
    }
)
class AttributeValueField(serializers.Field):  # type: ignore[type-arg]
    """Typed attribute value rendered as a string (``source="*"``)."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["source"] = "*"
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def to_representation(self, value: AttributeValue) -> str:
        if value.value_type == AttributeValueType.DECIMAL and value.value_decimal is not None:
            return format_decimal(value.value_decimal)
        if value.value_type == AttributeValueType.BOOLEAN:
            return "true" if value.value_boolean else "false"
        return value.value_text or ""
