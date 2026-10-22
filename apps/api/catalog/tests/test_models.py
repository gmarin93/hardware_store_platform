"""Database constraints and same-organization integrity (real PostgreSQL)."""

from collections.abc import Callable
from decimal import Decimal
from functools import partial
from typing import Any

import pytest
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from catalog.models import (
    AttributeValue,
    AttributeValueType,
    Media,
    Product,
    SourceReference,
    Unit,
    Variant,
)
from catalog.tests import factories as cf
from catalog.tests.fixtures import SHARED_SKU, CatalogWorld
from tests.fixtures import World

pytestmark = pytest.mark.django_db


def _rejected(action: Callable[[], Any], constraint: str) -> None:
    with pytest.raises(IntegrityError) as excinfo, transaction.atomic():
        action()
    assert constraint in str(excinfo.value)


def _variants(catalog: CatalogWorld) -> Any:
    return Variant.objects.filter(pk=catalog.variant.pk)


def test_quantity_columns_are_numeric_14_3() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, data_type, numeric_precision, numeric_scale "
            "FROM information_schema.columns WHERE table_name = 'catalog_variant' "
            "AND column_name IN ('quantity_increment', 'min_quantity') ORDER BY column_name"
        )
        assert cursor.fetchall() == [
            ("min_quantity", "numeric", 14, 3),
            ("quantity_increment", "numeric", 14, 3),
        ]


def test_sku_is_unique_per_organization_only(world: World, catalog: CatalogWorld) -> None:
    assert catalog.variant_b.sku == catalog.variant.sku == SHARED_SKU
    _rejected(lambda: cf.make_variant(catalog.product, SHARED_SKU), "catalog_variant_unique_sku")
    # Normalized on save: a lowercase duplicate is still a duplicate.
    _rejected(lambda: cf.make_variant(catalog.product, " sin-a-001 "), "catalog_variant_unique_sku")


def test_sku_is_stored_uppercase(catalog: CatalogWorld) -> None:
    variant = cf.make_variant(catalog.product, "  sin-a-lower ")
    assert variant.sku == "SIN-A-LOWER"
    _rejected(lambda: _variants(catalog).update(sku="sin-a-001"), "catalog_variant_sku_format")
    _rejected(lambda: _variants(catalog).update(sku="SIN A"), "catalog_variant_sku_format")


@pytest.mark.parametrize(
    ("changes", "constraint"),
    [
        ({"stock_unit": Unit.KG}, "catalog_variant_sales_eq_stock_unit"),
        ({"sales_unit": "lb", "stock_unit": "lb"}, "catalog_variant_sales_unit_known"),
        ({"quantity_increment": Decimal(0)}, "catalog_variant_increment_positive"),
        ({"quantity_increment": Decimal("-1")}, "catalog_variant_increment_positive"),
        ({"min_quantity": Decimal(0)}, "catalog_variant_min_qty_positive"),
        ({"status": "BORRADOR"}, "catalog_variant_status_known"),
        (
            {"quantity_increment": Decimal("0.25"), "min_quantity": Decimal("0.3")},
            "catalog_variant_min_qty_multiple",
        ),
    ],
)
def test_variant_check_constraints(
    catalog: CatalogWorld, changes: dict[str, Any], constraint: str
) -> None:
    _rejected(lambda: _variants(catalog).update(**changes), constraint)


def test_valid_fractional_rules_are_accepted(catalog: CatalogWorld) -> None:
    _variants(catalog).update(
        sales_unit=Unit.KG,
        stock_unit=Unit.KG,
        quantity_increment=Decimal("0.001"),
        min_quantity=Decimal("0.100"),
    )
    _variants(catalog).update(quantity_increment=Decimal("0.25"), min_quantity=Decimal("0.75"))
    catalog.variant.refresh_from_db()
    assert catalog.variant.min_quantity == Decimal("0.750")


def test_product_status_is_constrained(catalog: CatalogWorld) -> None:
    _rejected(
        lambda: Product.objects.filter(pk=catalog.product.pk).update(status="PUBLICADO"),
        "catalog_product_status_known",
    )


def test_cross_organization_links_are_rejected_by_service(
    world: World, catalog: CatalogWorld
) -> None:
    with pytest.raises(ValidationError):
        Variant.objects.create(
            organization=world.org_b,
            product=catalog.product,
            sku="SIN-CRUCE-2",
            name="Cruce (SINTÉTICO)",
            sales_unit=Unit.PIECE,
            stock_unit=Unit.PIECE,
            quantity_increment=Decimal(1),
            min_quantity=Decimal(1),
        )
    with pytest.raises(ValidationError):
        cf.make_product(world.org_b, "Cruce SINTÉTICO", brand=catalog.brand_a)
    with pytest.raises(ValidationError):
        cf.make_media(catalog.product, "/catalog-media/x.svg", variant=catalog.variant_b)
    with pytest.raises(ValidationError):
        cf.make_source(world.org_b, "CRUCE", product=catalog.product)


def test_cross_organization_links_are_rejected_by_database(
    world: World, catalog: CatalogWorld
) -> None:
    # Bulk updates bypass save(); composite foreign keys still refuse them.
    _rejected(
        lambda: Variant.objects.filter(pk=catalog.variant_draft.pk).update(
            organization=world.org_b
        ),
        "catalog_variant_product_same_org",
    )
    _rejected(
        lambda: Product.objects.filter(pk=catalog.product_b.pk).update(brand=catalog.brand_a),
        "catalog_product_brand_same_org",
    )
    _rejected(
        lambda: Product.objects.filter(pk=catalog.product_b.pk).update(category=catalog.category_a),
        "catalog_product_category_same_org",
    )
    other_variant = cf.make_variant(catalog.product_draft, "SIN-A-OTRO")
    _rejected(
        lambda: Media.objects.filter(pk=catalog.variant_media_approved.pk).update(
            variant=other_variant
        ),
        "catalog_media_variant_same_product",
    )
    _rejected(
        lambda: SourceReference.objects.filter(product=catalog.product).update(
            organization=world.org_b
        ),
        "catalog_source_product_same_org",
    )


def test_attribute_values_are_typed(world: World, catalog: CatalogWorld) -> None:
    length = AttributeValue.objects.get(variant=catalog.variant, definition__code="longitud")
    rows = AttributeValue.objects.filter(pk=length.pk)
    _rejected(lambda: rows.update(unit="in"), "catalog_attrval_definition_type_unit")
    _rejected(
        lambda: rows.update(
            value_type=AttributeValueType.TEXT, value_text="25.4", value_decimal=None
        ),
        "catalog_attrval_definition_type_unit",
    )
    _rejected(lambda: rows.update(value_text="25 mm"), "catalog_attrval_typed_value")
    _rejected(lambda: rows.update(product=catalog.product), "catalog_attrval_one_target")
    _rejected(lambda: rows.update(variant=None), "catalog_attrval_one_target")
    _rejected(lambda: rows.update(variant=catalog.variant_b), "catalog_attrval_variant_same_org")
    with pytest.raises(ValidationError):
        AttributeValue.objects.create(
            organization=world.org_a,
            definition=length.definition,
            variant=catalog.variant_draft,
            value_decimal=Decimal(1),
            unit="in",
        )


def test_media_urls_are_references_not_arbitrary_strings(catalog: CatalogWorld) -> None:
    rows = Media.objects.filter(pk=catalog.media_approved.pk)
    for url in (
        "javascript:alert(1)",
        "//host/x.png",  # protocol-relative
        "/\\host/x.png",
        "/",
        "http://example.test/x.png",
        "https://",
        "catalog/x.png",
        "/a b.png",
    ):
        _rejected(partial(rows.update, url=url), "catalog_media_url_format")
    rows.update(url="https://imagenes.example.test/aprobada.png")
    rows.update(url="/catalog-media/sintetico/otra.svg")


def test_source_urls_are_empty_or_https(catalog: CatalogWorld) -> None:
    rows = SourceReference.objects.filter(product=catalog.product)
    for url in ("javascript:alert(1)", "http://fuente.example.test/x", "//fuente/x", "https://"):
        _rejected(partial(rows.update, source_url=url), "catalog_source_url_https")
    rows.update(source_url="")
    rows.update(source_url="https://fuente.example.test/PROD-1")


def test_models_have_no_price_stock_or_availability_fields() -> None:
    names = {
        field.name.lower()
        for model in apps.get_app_config("catalog").get_models()
        for field in model._meta.get_fields()
    }
    forbidden = ("price", "precio", "cost", "availab", "on_hand", "reserved", "tax")
    assert not [n for n in names if any(f in n for f in forbidden)]
    assert [n for n in names if "stock" in n] == ["stock_unit"]


def test_catalog_tables_and_composite_keys_exist() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT conname FROM pg_constraint WHERE contype = 'f' AND array_length(conkey, 1) > 1 "
            "AND conrelid::regclass::text LIKE 'catalog_%' ORDER BY conname"
        )
        names = [row[0] for row in cursor.fetchall()]
    assert names == sorted(
        [
            "catalog_attrval_definition_same_org",
            "catalog_attrval_definition_type_unit",
            "catalog_attrval_product_same_org",
            "catalog_attrval_variant_same_org",
            "catalog_category_parent_same_org",
            "catalog_media_product_same_org",
            "catalog_media_variant_same_product",
            "catalog_product_brand_same_org",
            "catalog_product_category_same_org",
            "catalog_source_product_same_org",
            "catalog_source_variant_same_org",
            "catalog_variant_product_same_org",
        ]
    )
