"""Scoped catalog querysets. Views never build catalog querysets themselves.

Public selectors (``catalog.view_published``, every role): rows of the actor's
organization (guests: the default organization) with ``status = PUBLISHED``;
a variant also needs a PUBLISHED product. Nested rows are prefetched into
``public_*`` attributes that hold only published variants, published attribute
values and APPROVED media, so the public serializers cannot reach other rows.

Staff selectors (``catalog.view_staff_fields``: EMPLOYEE, ADMIN) return every
status of the actor's own organization and never another organization's rows.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.db.models import Model, Prefetch, Q, QuerySet

from accounts.permissions import Perm
from catalog.models import (
    AttributeValue,
    CatalogStatus,
    Media,
    MediaStatus,
    Product,
    SourceReference,
    Variant,
    normalize_sku,
)
from common.permissions import require_perm
from organizations.scope import Actor, scope_to_organization

PUBLISHED = CatalogStatus.PUBLISHED


def _in_org[M: Model](queryset: QuerySet[M], actor: Actor) -> QuerySet[M]:
    """Nested rows are scoped too (defense in depth; parents are already scoped)."""
    return scope_to_organization(queryset, actor)


# --- Public -----------------------------------------------------------------------


def _public_media(actor: Actor, *, variant_level: bool) -> QuerySet[Media]:
    return (
        _in_org(Media.objects.all(), actor)
        .filter(status=MediaStatus.APPROVED, variant__isnull=not variant_level)
        .order_by("sort_order", "id")
    )


def _public_attributes(actor: Actor) -> QuerySet[AttributeValue]:
    return (
        _in_org(AttributeValue.objects.all(), actor)
        .filter(is_published=True)
        .select_related("definition")
        .order_by("definition__code", "id")
    )


def _public_variant_prefetches(actor: Actor) -> tuple[Prefetch[Any, Any, Any], ...]:
    return (
        Prefetch(
            "media", queryset=_public_media(actor, variant_level=True), to_attr="public_media"
        ),
        Prefetch(
            "attribute_values", queryset=_public_attributes(actor), to_attr="public_attributes"
        ),
    )


def _published_products(actor: Actor) -> QuerySet[Product]:
    if not actor.has_perm(Perm.CATALOG_VIEW_PUBLISHED):
        return Product.objects.none()
    return scope_to_organization(Product.objects.all(), actor).filter(status=PUBLISHED)


def public_product_list(actor: Actor) -> QuerySet[Product]:
    return (
        _published_products(actor)
        .select_related("brand", "category")
        .prefetch_related(
            Prefetch(
                "media", queryset=_public_media(actor, variant_level=False), to_attr="public_media"
            )
        )
    )


def public_product_detail(actor: Actor) -> QuerySet[Product]:
    variants = (
        _in_org(Variant.objects.all(), actor)
        .filter(status=PUBLISHED)
        .order_by("sku", "id")
        .prefetch_related(*_public_variant_prefetches(actor))
    )
    return public_product_list(actor).prefetch_related(
        Prefetch(
            "attribute_values", queryset=_public_attributes(actor), to_attr="public_attributes"
        ),
        Prefetch("variants", queryset=variants, to_attr="public_variants"),
    )


def public_variants(actor: Actor) -> QuerySet[Variant]:
    if not actor.has_perm(Perm.CATALOG_VIEW_PUBLISHED):
        return Variant.objects.none()
    return (
        scope_to_organization(Variant.objects.all(), actor)
        .filter(status=PUBLISHED, product__status=PUBLISHED)
        .select_related("product", "product__brand", "product__category")
        .prefetch_related(*_public_variant_prefetches(actor))
    )


# --- Staff ------------------------------------------------------------------------


def _staff_media(actor: Actor, *, variant_level: bool) -> QuerySet[Media]:
    return (
        _in_org(Media.objects.all(), actor)
        .filter(variant__isnull=not variant_level)
        .order_by("sort_order", "id")
    )


def _staff_attributes(actor: Actor) -> QuerySet[AttributeValue]:
    return (
        _in_org(AttributeValue.objects.all(), actor)
        .select_related("definition")
        .order_by("definition__code", "id")
    )


def _staff_sources(actor: Actor) -> QuerySet[SourceReference]:
    return _in_org(SourceReference.objects.all(), actor).order_by(
        "source_name", "external_id", "id"
    )


def _staff_variant_prefetches(actor: Actor) -> tuple[Prefetch[Any, Any, Any], ...]:
    return (
        Prefetch("media", queryset=_staff_media(actor, variant_level=True), to_attr="staff_media"),
        Prefetch("attribute_values", queryset=_staff_attributes(actor), to_attr="staff_attributes"),
        Prefetch("source_references", queryset=_staff_sources(actor), to_attr="staff_sources"),
    )


def _staff_products(actor: Actor) -> QuerySet[Product]:
    require_perm(actor, Perm.CATALOG_VIEW_STAFF_FIELDS)
    return scope_to_organization(Product.objects.all(), actor)


def staff_product_list(actor: Actor) -> QuerySet[Product]:
    return (
        _staff_products(actor)
        .select_related("brand", "category")
        .prefetch_related(
            Prefetch(
                "media", queryset=_staff_media(actor, variant_level=False), to_attr="staff_media"
            )
        )
    )


def staff_product_detail(actor: Actor) -> QuerySet[Product]:
    variants = (
        _in_org(Variant.objects.all(), actor)
        .order_by("sku", "id")
        .prefetch_related(*_staff_variant_prefetches(actor))
    )
    return staff_product_list(actor).prefetch_related(
        Prefetch("attribute_values", queryset=_staff_attributes(actor), to_attr="staff_attributes"),
        Prefetch("source_references", queryset=_staff_sources(actor), to_attr="staff_sources"),
        Prefetch("variants", queryset=variants, to_attr="staff_variants"),
    )


def staff_variants(actor: Actor) -> QuerySet[Variant]:
    require_perm(actor, Perm.CATALOG_VIEW_STAFF_FIELDS)
    return (
        scope_to_organization(Variant.objects.all(), actor)
        .select_related("product", "product__brand", "product__category")
        .prefetch_related(*_staff_variant_prefetches(actor))
    )


# --- Filters ----------------------------------------------------------------------


def filter_products(
    queryset: QuerySet[Product],
    *,
    category: uuid.UUID | None = None,
    brand: uuid.UUID | None = None,
    q: str = "",
    status: str | None = None,
) -> QuerySet[Product]:
    """Exact category/brand ids, case-insensitive name substring (P1; fuzzy is P2)."""
    if category is not None:
        queryset = queryset.filter(category_id=category)
    if brand is not None:
        queryset = queryset.filter(brand_id=brand)
    if q:
        queryset = queryset.filter(Q(name__icontains=q))
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def filter_variants_by_sku(queryset: QuerySet[Variant], sku: str) -> QuerySet[Variant]:
    """Exact SKU match after canonicalization (strip + uppercase); no partial match."""
    return queryset.filter(sku=normalize_sku(sku))
