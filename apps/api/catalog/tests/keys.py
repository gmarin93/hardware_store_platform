"""Exact response key sets for public and staff catalog serializers."""

PUBLIC_PRODUCT_KEYS = {"id", "name", "description", "brand", "category", "media"}
PUBLIC_PRODUCT_DETAIL_KEYS = PUBLIC_PRODUCT_KEYS | {"attributes", "variants"}
PUBLIC_VARIANT_KEYS = {
    "id",
    "sku",
    "name",
    "sales_unit",
    "quantity_increment",
    "min_quantity",
    "attributes",
    "media",
}
PUBLIC_VARIANT_DETAIL_KEYS = PUBLIC_VARIANT_KEYS | {"product"}
PUBLIC_VARIANT_PRODUCT_KEYS = {"id", "name", "description", "brand", "category"}
PUBLIC_ATTRIBUTE_KEYS = {"code", "name", "value_type", "value", "unit"}
PUBLIC_MEDIA_KEYS = {"id", "url", "alt_text"}
TAXONOMY_KEYS = {"id", "name", "slug"}
PAGE_KEYS = {"results", "next_cursor", "previous_cursor"}

# Keys that only staff serializers may contain.
STAFF_ONLY_KEYS = {
    "status",
    "stock_unit",
    "supplier_code",
    "internal_notes",
    "source_references",
    "source_name",
    "source_url",
    "external_id",
    "observed_at",
    "is_synthetic",
    "is_published",
    "sort_order",
    "created_at",
    "updated_at",
}

STAFF_PRODUCT_KEYS = {
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
}
STAFF_PRODUCT_DETAIL_KEYS = STAFF_PRODUCT_KEYS | {"attributes", "variants", "source_references"}
STAFF_VARIANT_KEYS = {
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
}
STAFF_VARIANT_DETAIL_KEYS = STAFF_VARIANT_KEYS | {"product"}
STAFF_VARIANT_PRODUCT_KEYS = {"id", "name", "status", "brand", "category"}
STAFF_ATTRIBUTE_KEYS = {"id", "code", "name", "value_type", "value", "unit", "is_published"}
STAFF_MEDIA_KEYS = {"id", "url", "alt_text", "status", "sort_order"}
SOURCE_KEYS = {"id", "source_name", "external_id", "source_url", "observed_at", "is_synthetic"}
