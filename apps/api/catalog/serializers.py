"""Catalog serializers. Public and staff representations are separate classes
(separate OpenAPI components); tests pin the exact key sets.

Public allowlist (ADR 0001): id, sku, name, description, brand, category,
published attributes, approved media, sales unit, increment, min_quantity.
Staff-only: status, stock_unit, internal notes, supplier codes, draft media,
unpublished attributes, SourceReference provenance (incl. source URLs),
timestamps. Nothing here exposes price, cost, stock or availability.

Public serializers read only the ``public_*`` prefetch attributes built by
``catalog.selectors``; staff serializers read ``staff_*``. A queryset without
those prefetches fails loudly instead of falling back to unfiltered relations.
"""

from typing import Any

from rest_framework import serializers

from catalog.fields import (
    AttributeUnitField,
    AttributeValueField,
    AttributeValueTypeField,
    CatalogStatusField,
    MediaStatusField,
    UnitField,
)
from catalog.models import AttributeValue, Brand, Category, Media, Product, SourceReference, Variant

# --- Shared taxonomy (no staff fields exist on brands/categories) ------------------


class BrandSummarySerializer(serializers.ModelSerializer[Brand]):
    class Meta:
        model = Brand
        fields: Any = ("id", "name", "slug")
        read_only_fields = fields


class CategorySummarySerializer(serializers.ModelSerializer[Category]):
    class Meta:
        model = Category
        fields: Any = ("id", "name", "slug")
        read_only_fields = fields


# --- Public -----------------------------------------------------------------------


class PublicMediaSerializer(serializers.ModelSerializer[Media]):
    class Meta:
        model = Media
        fields: Any = ("id", "url", "alt_text")
        read_only_fields = fields


class PublicAttributeSerializer(serializers.ModelSerializer[AttributeValue]):
    code = serializers.CharField(source="definition.code", read_only=True)
    name = serializers.CharField(source="definition.name", read_only=True)
    value_type = AttributeValueTypeField()
    value = AttributeValueField()
    unit = AttributeUnitField()

    class Meta:
        model = AttributeValue
        fields: Any = ("code", "name", "value_type", "value", "unit")
        read_only_fields = fields


class PublicVariantSerializer(serializers.ModelSerializer[Variant]):
    """A published variant as embedded in a public product."""

    sales_unit = UnitField()
    attributes = PublicAttributeSerializer(source="public_attributes", many=True, read_only=True)
    media = PublicMediaSerializer(source="public_media", many=True, read_only=True)

    class Meta:
        model = Variant
        fields: Any = (
            "id",
            "sku",
            "name",
            "sales_unit",
            "quantity_increment",
            "min_quantity",
            "attributes",
            "media",
        )
        read_only_fields = fields


class PublicVariantProductSerializer(serializers.ModelSerializer[Product]):
    brand = BrandSummarySerializer(read_only=True, allow_null=True)
    category = CategorySummarySerializer(read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields: Any = ("id", "name", "description", "brand", "category")
        read_only_fields = fields


class PublicVariantDetailSerializer(PublicVariantSerializer):
    """``GET /catalog/variants/{id}`` and ``GET /catalog/variants?sku=`` items."""

    product = PublicVariantProductSerializer(read_only=True)

    class Meta(PublicVariantSerializer.Meta):
        fields: Any = (*PublicVariantSerializer.Meta.fields, "product")
        read_only_fields = fields


class PublicProductSerializer(serializers.ModelSerializer[Product]):
    """``GET /catalog/products`` items."""

    brand = BrandSummarySerializer(read_only=True, allow_null=True)
    category = CategorySummarySerializer(read_only=True, allow_null=True)
    media = PublicMediaSerializer(source="public_media", many=True, read_only=True)

    class Meta:
        model = Product
        fields: Any = ("id", "name", "description", "brand", "category", "media")
        read_only_fields = fields


class PublicProductDetailSerializer(PublicProductSerializer):
    """``GET /catalog/products/{id}``: published variants embedded."""

    attributes = PublicAttributeSerializer(source="public_attributes", many=True, read_only=True)
    variants = PublicVariantSerializer(source="public_variants", many=True, read_only=True)

    class Meta(PublicProductSerializer.Meta):
        fields: Any = (*PublicProductSerializer.Meta.fields, "attributes", "variants")
        read_only_fields = fields


# --- Staff ------------------------------------------------------------------------


class StaffMediaSerializer(serializers.ModelSerializer[Media]):
    status = MediaStatusField()

    class Meta:
        model = Media
        fields: Any = ("id", "url", "alt_text", "status", "sort_order")
        read_only_fields = fields


class StaffAttributeSerializer(PublicAttributeSerializer):
    class Meta(PublicAttributeSerializer.Meta):
        fields: Any = ("id", *PublicAttributeSerializer.Meta.fields, "is_published")
        read_only_fields = fields


class SourceReferenceSerializer(serializers.ModelSerializer[SourceReference]):
    class Meta:
        model = SourceReference
        fields: Any = (
            "id",
            "source_name",
            "external_id",
            "source_url",
            "observed_at",
            "is_synthetic",
        )
        read_only_fields = fields


class StaffVariantSerializer(serializers.ModelSerializer[Variant]):
    status = CatalogStatusField()
    sales_unit = UnitField()
    stock_unit = UnitField()
    attributes = StaffAttributeSerializer(source="staff_attributes", many=True, read_only=True)
    media = StaffMediaSerializer(source="staff_media", many=True, read_only=True)
    source_references = SourceReferenceSerializer(source="staff_sources", many=True, read_only=True)

    class Meta:
        model = Variant
        fields: Any = (
            "id",
            "sku",
            "name",
            "status",
            "sales_unit",
            "stock_unit",
            "quantity_increment",
            "min_quantity",
            "supplier_code",
            "internal_notes",
            "attributes",
            "media",
            "source_references",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class StaffVariantProductSerializer(serializers.ModelSerializer[Product]):
    status = CatalogStatusField()
    brand = BrandSummarySerializer(read_only=True, allow_null=True)
    category = CategorySummarySerializer(read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields: Any = ("id", "name", "status", "brand", "category")
        read_only_fields = fields


class StaffVariantDetailSerializer(StaffVariantSerializer):
    product = StaffVariantProductSerializer(read_only=True)

    class Meta(StaffVariantSerializer.Meta):
        fields: Any = (*StaffVariantSerializer.Meta.fields, "product")
        read_only_fields = fields


class StaffProductSerializer(serializers.ModelSerializer[Product]):
    status = CatalogStatusField()
    brand = BrandSummarySerializer(read_only=True, allow_null=True)
    category = CategorySummarySerializer(read_only=True, allow_null=True)
    media = StaffMediaSerializer(source="staff_media", many=True, read_only=True)

    class Meta:
        model = Product
        fields: Any = (
            "id",
            "name",
            "description",
            "brand",
            "category",
            "status",
            "internal_notes",
            "media",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class StaffProductDetailSerializer(StaffProductSerializer):
    attributes = StaffAttributeSerializer(source="staff_attributes", many=True, read_only=True)
    variants = StaffVariantSerializer(source="staff_variants", many=True, read_only=True)
    source_references = SourceReferenceSerializer(source="staff_sources", many=True, read_only=True)

    class Meta(StaffProductSerializer.Meta):
        fields: Any = (
            *StaffProductSerializer.Meta.fields,
            "attributes",
            "variants",
            "source_references",
        )
        read_only_fields = fields


# --- Query parameters -------------------------------------------------------------


class ProductQuerySerializer(serializers.Serializer[Any]):
    category = serializers.UUIDField(
        required=False, help_text="Id exacto de categoría (sin subcategorías)."
    )
    brand = serializers.UUIDField(required=False, help_text="Id exacto de marca.")
    q = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        help_text="Texto contenido en el nombre (sin distinguir mayúsculas). Búsqueda difusa: P2.",
    )


class StaffProductQuerySerializer(ProductQuerySerializer):
    status = CatalogStatusField(read_only=False, required=False, help_text="Filtrar por estado.")


class SkuQuerySerializer(serializers.Serializer[Any]):
    sku = serializers.CharField(
        max_length=64,
        help_text=(
            "SKU exacto. Se eliminan espacios al inicio y al final y se compara en "
            "mayúsculas (los SKU se guardan en mayúsculas); no hay coincidencia parcial."
        ),
    )
