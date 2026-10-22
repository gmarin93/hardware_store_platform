"""Synthetic catalog factories (names carry "SINTÉTICO"; no real store data)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from catalog.models import (
    AttributeDefinition,
    AttributeValue,
    AttributeValueType,
    Brand,
    CatalogStatus,
    Category,
    Media,
    MediaStatus,
    Product,
    SourceReference,
    Unit,
    Variant,
)
from organizations.models import Organization


def make_brand(org: Organization, slug: str = "marca-ficticia", **extra: Any) -> Brand:
    extra.setdefault("name", f"Marca {slug} (SINTÉTICO)")
    return Brand.objects.create(organization=org, slug=slug, **extra)


def make_category(org: Organization, slug: str = "categoria-ficticia", **extra: Any) -> Category:
    extra.setdefault("name", f"Categoría {slug} (SINTÉTICO)")
    return Category.objects.create(organization=org, slug=slug, **extra)


def make_product(
    org: Organization,
    name: str = "Producto SINTÉTICO",
    status: str = CatalogStatus.PUBLISHED,
    **extra: Any,
) -> Product:
    extra.setdefault("description", f"Descripción de {name} (SINTÉTICO)")
    return Product.objects.create(organization=org, name=name, status=status, **extra)


def make_variant(
    product: Product,
    sku: str,
    status: str = CatalogStatus.PUBLISHED,
    unit: str = Unit.PIECE,
    increment: str = "1",
    min_quantity: str = "1",
    **extra: Any,
) -> Variant:
    extra.setdefault("name", f"Variante {sku} (SINTÉTICO)")
    return Variant.objects.create(
        organization_id=product.organization_id,
        product=product,
        sku=sku,
        status=status,
        sales_unit=unit,
        stock_unit=unit,
        quantity_increment=Decimal(increment),
        min_quantity=Decimal(min_quantity),
        **extra,
    )


def make_definition(
    org: Organization, code: str, value_type: str = AttributeValueType.TEXT, unit: str = ""
) -> AttributeDefinition:
    return AttributeDefinition.objects.create(
        organization=org, code=code, name=f"Atributo {code}", value_type=value_type, unit=unit
    )


def make_attribute(
    definition: AttributeDefinition,
    value: Any,
    *,
    product: Product | None = None,
    variant: Variant | None = None,
    published: bool = True,
) -> AttributeValue:
    typed: dict[str, Any] = {}
    if definition.value_type == AttributeValueType.DECIMAL:
        typed["value_decimal"] = Decimal(value)
    elif definition.value_type == AttributeValueType.BOOLEAN:
        typed["value_boolean"] = value
    else:
        typed["value_text"] = value
    return AttributeValue.objects.create(
        organization_id=definition.organization_id,
        definition=definition,
        product=product,
        variant=variant,
        is_published=published,
        **typed,
    )


def make_media(
    product: Product,
    url: str,
    status: str = MediaStatus.APPROVED,
    variant: Variant | None = None,
    **extra: Any,
) -> Media:
    extra.setdefault("alt_text", "Imagen de prueba (SINTÉTICO)")
    return Media.objects.create(
        organization_id=product.organization_id,
        product=product,
        variant=variant,
        url=url,
        status=status,
        **extra,
    )


def make_source(
    org: Organization,
    external_id: str,
    *,
    product: Product | None = None,
    variant: Variant | None = None,
) -> SourceReference:
    return SourceReference.objects.create(
        organization=org,
        product=product,
        variant=variant,
        source_name="Fuente de prueba SINTÉTICA",
        external_id=external_id,
        source_url=f"https://fuente.example.test/{external_id}",
        observed_at=datetime(2026, 10, 21, 12, 0, tzinfo=UTC),
        is_synthetic=True,
    )
