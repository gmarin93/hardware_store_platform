"""OpenAPI contract for the catalog (generated in-process; the committed
``contracts/openapi.yaml`` is checked by the regenerate-and-diff command)."""

from typing import Any

import pytest
from drf_spectacular.generators import SchemaGenerator

from catalog.tests.keys import (
    PUBLIC_ATTRIBUTE_KEYS,
    PUBLIC_MEDIA_KEYS,
    PUBLIC_PRODUCT_DETAIL_KEYS,
    PUBLIC_PRODUCT_KEYS,
    PUBLIC_VARIANT_DETAIL_KEYS,
    PUBLIC_VARIANT_KEYS,
    PUBLIC_VARIANT_PRODUCT_KEYS,
    SOURCE_KEYS,
    STAFF_ATTRIBUTE_KEYS,
    STAFF_MEDIA_KEYS,
    STAFF_ONLY_KEYS,
    STAFF_PRODUCT_DETAIL_KEYS,
    STAFF_PRODUCT_KEYS,
    STAFF_VARIANT_DETAIL_KEYS,
    STAFF_VARIANT_KEYS,
    STAFF_VARIANT_PRODUCT_KEYS,
)


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    generator = SchemaGenerator()  # type: ignore[no-untyped-call]
    generated: dict[str, Any] = generator.get_schema(request=None, public=True)  # type: ignore[no-untyped-call]
    return generated


def _props(schema: dict[str, Any], component: str) -> set[str]:
    return set(schema["components"]["schemas"][component]["properties"])


def test_contract_version(schema: dict[str, Any]) -> None:
    assert schema["info"]["version"] == "0.1.0"


def test_catalog_operations_are_get_only(schema: dict[str, Any]) -> None:
    catalog_paths = {p: ops for p, ops in schema["paths"].items() if "/catalog/" in p}
    assert set(catalog_paths) == {
        "/api/v1/catalog/products",
        "/api/v1/catalog/products/{product_id}",
        "/api/v1/catalog/variants",
        "/api/v1/catalog/variants/{variant_id}",
        "/api/v1/catalog/staff/products",
        "/api/v1/catalog/staff/products/{product_id}",
        "/api/v1/catalog/staff/variants",
        "/api/v1/catalog/staff/variants/{variant_id}",
    }
    operation_ids = set()
    for ops in catalog_paths.values():
        assert set(ops) - {"parameters"} == {"get"}
        operation_ids.add(ops["get"]["operationId"])
    assert operation_ids == {
        "catalog_products_list",
        "catalog_products_retrieve",
        "catalog_variants_list",
        "catalog_variants_retrieve",
        "catalog_staff_products_list",
        "catalog_staff_products_retrieve",
        "catalog_staff_variants_list",
        "catalog_staff_variants_retrieve",
    }


@pytest.mark.parametrize(
    ("component", "keys"),
    [
        ("PublicProduct", PUBLIC_PRODUCT_KEYS),
        ("PublicProductDetail", PUBLIC_PRODUCT_DETAIL_KEYS),
        ("PublicVariant", PUBLIC_VARIANT_KEYS),
        ("PublicVariantDetail", PUBLIC_VARIANT_DETAIL_KEYS),
        ("PublicVariantProduct", PUBLIC_VARIANT_PRODUCT_KEYS),
        ("PublicAttribute", PUBLIC_ATTRIBUTE_KEYS),
        ("PublicMedia", PUBLIC_MEDIA_KEYS),
        ("StaffProduct", STAFF_PRODUCT_KEYS),
        ("StaffProductDetail", STAFF_PRODUCT_DETAIL_KEYS),
        ("StaffVariant", STAFF_VARIANT_KEYS),
        ("StaffVariantDetail", STAFF_VARIANT_DETAIL_KEYS),
        ("StaffVariantProduct", STAFF_VARIANT_PRODUCT_KEYS),
        ("StaffAttribute", STAFF_ATTRIBUTE_KEYS),
        ("StaffMedia", STAFF_MEDIA_KEYS),
        ("SourceReference", SOURCE_KEYS),
    ],
)
def test_component_key_sets(schema: dict[str, Any], component: str, keys: set[str]) -> None:
    assert _props(schema, component) == keys
    if component.startswith("Public"):
        assert not _props(schema, component) & STAFF_ONLY_KEYS


def test_public_operations_reference_only_public_components(schema: dict[str, Any]) -> None:
    def refs(node: Any) -> set[str]:
        if isinstance(node, dict):
            found = {node["$ref"].rsplit("/", 1)[-1]} if "$ref" in node else set()
            return found | {r for v in node.values() for r in refs(v)}
        if isinstance(node, list):
            return {r for item in node for r in refs(item)}
        return set()

    components = schema["components"]["schemas"]

    def closure(names: set[str]) -> set[str]:
        seen: set[str] = set()
        todo = set(names)
        while todo:
            name = todo.pop()
            if name in seen:
                continue
            seen.add(name)
            todo |= refs(components.get(name, {}))
        return seen

    for path, ops in schema["paths"].items():
        if path.startswith("/api/v1/catalog/") and "/staff/" not in path:
            used = closure(refs(ops["get"]["responses"]["200"]))
            assert not {n for n in used if n.startswith("Staff") or n == "SourceReference"}
            assert "PublicMedia" in used


def test_schema_has_no_price_or_availability_fields(schema: dict[str, Any]) -> None:
    names: set[str] = set()
    for component in schema["components"]["schemas"].values():
        names |= set(component.get("properties", {}))
    forbidden = ("price", "precio", "cost", "availab", "on_hand", "reserved", "tax")
    assert not [n for n in names if any(f in n.lower() for f in forbidden)]
    assert [n for n in names if "stock" in n] == ["stock_unit"]
    assert not [p for p in schema["paths"] if any(f in p for f in ("price", "availab"))]
