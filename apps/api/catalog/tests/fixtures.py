"""``catalog`` fixture: synthetic catalog rows on top of the shared ``world``.

org_a (default organization) holds published, draft and archived products,
variants, media and attributes plus staff-only fields carrying marker strings
(``HIDDEN_MARKERS``) that must never appear in public responses. org_b holds a
published product whose variant reuses org_a's SKU.
"""

from dataclasses import dataclass
from typing import Any

import pytest

from catalog.models import (
    AttributeValueType,
    Brand,
    CatalogStatus,
    Category,
    Media,
    MediaStatus,
    Product,
    Unit,
    Variant,
)
from catalog.tests import factories as cf
from tests.fixtures import World

__all__ = ["HIDDEN_MARKERS", "SHARED_SKU", "CatalogWorld", "catalog"]

SHARED_SKU = "SIN-A-001"

# Values present only in staff-only fields or unpublished rows of org_a/org_b.
HIDDEN_MARKERS = (
    "NOTA-INTERNA-PRODUCTO",
    "NOTA-INTERNA-VARIANTE",
    "PROV-OCULTO-1",
    "SIN-A-DRAFT",
    "SIN-A-ARCH",
    "SIN-A-DRAFTPROD",
    "/catalog-media/sintetico/borrador.svg",
    "/catalog-media/sintetico/variante-borrador.svg",
    "nota-oculta",
    "fuente.example.test",
    "Fuente de prueba",
    "Producto borrador SINTÉTICO",
    "Producto archivado SINTÉTICO",
    "Producto de otra organización SINTÉTICO",
)


@dataclass
class CatalogWorld:
    brand_a: Brand
    category_a: Category
    brand_b: Brand
    category_b: Category
    product: Product
    product_draft: Product
    product_archived: Product
    product_b: Product
    variant: Variant
    variant_draft: Variant
    variant_archived: Variant
    variant_of_draft_product: Variant
    variant_b: Variant
    media_approved: Media
    media_draft: Media
    variant_media_approved: Media


@pytest.fixture
def catalog(world: World) -> CatalogWorld:
    org_a, org_b = world.org_a, world.org_b
    brand_a = cf.make_brand(org_a, "alfa")
    category_a = cf.make_category(org_a, "tornilleria")
    brand_b = cf.make_brand(org_b, "delta")
    category_b = cf.make_category(org_b, "tornilleria")

    product = cf.make_product(
        org_a,
        "Tornillo publicado SINTÉTICO",
        brand=brand_a,
        category=category_a,
        internal_notes="NOTA-INTERNA-PRODUCTO",
    )
    variant = cf.make_variant(
        product, SHARED_SKU, supplier_code="PROV-OCULTO-1", internal_notes="NOTA-INTERNA-VARIANTE"
    )
    variant_draft = cf.make_variant(product, "SIN-A-DRAFT", status=CatalogStatus.DRAFT)
    variant_archived = cf.make_variant(product, "SIN-A-ARCH", status=CatalogStatus.ARCHIVED)

    material = cf.make_definition(org_a, "material")
    length = cf.make_definition(org_a, "longitud", AttributeValueType.DECIMAL, "mm")
    outdoor = cf.make_definition(org_a, "uso-exterior", AttributeValueType.BOOLEAN)
    hidden = cf.make_definition(org_a, "nota-oculta")
    cf.make_attribute(material, "Acero zincado", product=product)
    cf.make_attribute(outdoor, False, product=product)
    cf.make_attribute(hidden, "dato interno", product=product, published=False)
    cf.make_attribute(length, "25.400", variant=variant)
    cf.make_attribute(hidden, "dato interno variante", variant=variant, published=False)

    media_approved = cf.make_media(product, "/catalog-media/sintetico/aprobada.svg")
    media_draft = cf.make_media(
        product, "/catalog-media/sintetico/borrador.svg", status=MediaStatus.DRAFT, sort_order=1
    )
    variant_media_approved = cf.make_media(
        product, "/catalog-media/sintetico/variante.svg", variant=variant
    )
    cf.make_media(
        product,
        "/catalog-media/sintetico/variante-borrador.svg",
        status=MediaStatus.DRAFT,
        variant=variant,
    )
    cf.make_source(org_a, "PROD-1", product=product)
    cf.make_source(org_a, "VAR-1", variant=variant)

    product_draft = cf.make_product(
        org_a, "Producto borrador SINTÉTICO", status=CatalogStatus.DRAFT, brand=brand_a
    )
    variant_of_draft_product = cf.make_variant(product_draft, "SIN-A-DRAFTPROD")
    product_archived = cf.make_product(
        org_a, "Producto archivado SINTÉTICO", status=CatalogStatus.ARCHIVED
    )
    cf.make_variant(product_archived, "SIN-A-ARCHPROD", status=CatalogStatus.ARCHIVED)

    product_b = cf.make_product(
        org_b, "Producto de otra organización SINTÉTICO", brand=brand_b, category=category_b
    )
    variant_b = cf.make_variant(product_b, SHARED_SKU, unit=Unit.KG, increment="0.5")

    return CatalogWorld(
        brand_a=brand_a,
        category_a=category_a,
        brand_b=brand_b,
        category_b=category_b,
        product=product,
        product_draft=product_draft,
        product_archived=product_archived,
        product_b=product_b,
        variant=variant,
        variant_draft=variant_draft,
        variant_archived=variant_archived,
        variant_of_draft_product=variant_of_draft_product,
        variant_b=variant_b,
        media_approved=media_approved,
        media_draft=media_draft,
        variant_media_approved=variant_media_approved,
    )


def all_keys(data: Any) -> set[str]:
    """Every dict key at any depth of a JSON value."""
    if isinstance(data, dict):
        return set(data) | {k for v in data.values() for k in all_keys(v)}
    if isinstance(data, list):
        return {k for item in data for k in all_keys(item)}
    return set()
