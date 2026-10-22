"""Public catalog API: guests and customers of the default organization."""

import uuid
from typing import Any

import pytest
from django.core import signing
from django.test import Client

from accounts.models import User
from catalog.models import CatalogStatus
from catalog.tests import factories as cf
from catalog.tests.fixtures import HIDDEN_MARKERS, SHARED_SKU, CatalogWorld, all_keys
from catalog.tests.keys import (
    PAGE_KEYS,
    PUBLIC_ATTRIBUTE_KEYS,
    PUBLIC_MEDIA_KEYS,
    PUBLIC_PRODUCT_DETAIL_KEYS,
    PUBLIC_PRODUCT_KEYS,
    PUBLIC_VARIANT_DETAIL_KEYS,
    PUBLIC_VARIANT_KEYS,
    PUBLIC_VARIANT_PRODUCT_KEYS,
    STAFF_ONLY_KEYS,
    TAXONOMY_KEYS,
)
from catalog.views import PRODUCT_ORDERING, VARIANT_ORDERING
from common.pagination import CURSOR_SALT
from tests.fixtures import API, World

pytestmark = pytest.mark.django_db

SAME_REQUEST_ID = "catalog-404-check"

# P1 exposes no commercial or inventory data at all (D07/D09).
FORBIDDEN_FRAGMENTS = ("price", "precio", "cost", "availab", "on_hand", "reserved", "tax")


def _client(user: User | None = None) -> Client:
    client = Client()
    if user is not None:
        client.force_login(user)
    return client


def _get(client: Client, path: str, **params: Any) -> Any:
    return client.get(f"{API}{path}", params, headers={"X-Request-ID": SAME_REQUEST_ID})


def _assert_public_payload(response: Any) -> None:
    body = response.content.decode()
    keys = all_keys(response.json())
    assert not keys & STAFF_ONLY_KEYS
    assert not [k for k in keys if any(f in k.lower() for f in FORBIDDEN_FRAGMENTS)]
    assert not [k for k in keys if "stock" in k.lower()]
    for marker in HIDDEN_MARKERS:
        assert marker not in body, marker


def _assert_same_as_nonexistent(client: Client, prefix: str, hidden_id: object) -> None:
    hidden = _get(client, f"{prefix}/{hidden_id}")
    missing = _get(client, f"{prefix}/{uuid.uuid4()}")
    assert hidden.status_code == missing.status_code == 404
    assert hidden.content == missing.content
    assert dict(hidden.headers) == dict(missing.headers)
    assert hidden.json() == {
        "code": "NOT_FOUND",
        "message": "El recurso solicitado no existe.",
        "field_errors": {},
        "request_id": SAME_REQUEST_ID,
    }


# --- Products ---------------------------------------------------------------------


@pytest.mark.parametrize("role", ["guest", "customer"])
def test_product_list_has_only_published_products_of_default_org(
    world: World, catalog: CatalogWorld, role: str
) -> None:
    client = _client(world.customer_a if role == "customer" else None)
    response = _get(client, "/catalog/products")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == PAGE_KEYS
    assert [row["id"] for row in data["results"]] == [str(catalog.product.id)]
    row = data["results"][0]
    assert set(row) == PUBLIC_PRODUCT_KEYS
    assert set(row["brand"]) == TAXONOMY_KEYS
    assert set(row["category"]) == TAXONOMY_KEYS
    assert [m["url"] for m in row["media"]] == [catalog.media_approved.url]
    assert set(row["media"][0]) == PUBLIC_MEDIA_KEYS
    _assert_public_payload(response)


def test_product_detail_embeds_only_published_variants_attributes_and_media(
    catalog: CatalogWorld,
) -> None:
    response = _get(_client(), f"/catalog/products/{catalog.product.id}")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == PUBLIC_PRODUCT_DETAIL_KEYS
    assert [v["id"] for v in data["variants"]] == [str(catalog.variant.id)]
    variant = data["variants"][0]
    assert set(variant) == PUBLIC_VARIANT_KEYS
    assert variant == {
        "id": str(catalog.variant.id),
        "sku": SHARED_SKU,
        "name": catalog.variant.name,
        "sales_unit": "piece",
        "quantity_increment": "1.000",
        "min_quantity": "1.000",
        "attributes": [
            {
                "code": "longitud",
                "name": "Atributo longitud",
                "value_type": "DECIMAL",
                "value": "25.4",
                "unit": "mm",
            }
        ],
        "media": [
            {
                "id": str(catalog.variant_media_approved.id),
                "url": "/catalog-media/sintetico/variante.svg",
                "alt_text": "Imagen de prueba (SINTÉTICO)",
            }
        ],
    }
    assert data["attributes"] == [
        {
            "code": "material",
            "name": "Atributo material",
            "value_type": "TEXT",
            "value": "Acero zincado",
            "unit": None,
        },
        {
            "code": "uso-exterior",
            "name": "Atributo uso-exterior",
            "value_type": "BOOLEAN",
            "value": "false",
            "unit": None,
        },
    ]
    for attribute in data["attributes"]:
        assert set(attribute) == PUBLIC_ATTRIBUTE_KEYS
    assert [m["id"] for m in data["media"]] == [str(catalog.media_approved.id)]
    _assert_public_payload(response)


@pytest.mark.parametrize("role", ["guest", "customer", "admin_a"])
def test_hidden_products_are_404_identical_to_nonexistent(
    world: World, catalog: CatalogWorld, role: str
) -> None:
    # Public endpoints never reveal unpublished rows, even to staff of the organization.
    user = {"guest": None, "customer": world.customer_a, "admin_a": world.admin_a}[role]
    client = _client(user)
    for hidden in (
        catalog.product_draft.id,
        catalog.product_archived.id,
        catalog.product_b.id,
        "not-a-uuid",
        "123",
    ):
        _assert_same_as_nonexistent(client, "/catalog/products", hidden)


def test_staff_of_other_org_sees_own_published_catalog_on_public_endpoints(
    world: World, catalog: CatalogWorld
) -> None:
    client = _client(world.employee_b1)
    ids = [row["id"] for row in _get(client, "/catalog/products").json()["results"]]
    assert ids == [str(catalog.product_b.id)]
    _assert_same_as_nonexistent(client, "/catalog/products", catalog.product.id)


def test_product_filters(world: World, catalog: CatalogWorld) -> None:
    client = _client()
    other = cf.make_product(world.org_a, "Bisagra pública SINTÉTICO")

    def ids(**params: Any) -> list[str]:
        response = _get(client, "/catalog/products", **params)
        assert response.status_code == 200
        return [row["id"] for row in response.json()["results"]]

    assert ids() == [str(other.id), str(catalog.product.id)]
    assert ids(category=str(catalog.category_a.id)) == [str(catalog.product.id)]
    assert ids(brand=str(catalog.brand_a.id)) == [str(catalog.product.id)]
    assert ids(q="TORNILLO") == [str(catalog.product.id)]
    assert ids(q="  bisagra ") == [str(other.id)]
    assert ids(q="") == [str(other.id), str(catalog.product.id)]
    assert ids(q="borrador") == []  # draft product names are not searchable
    assert ids(category=str(catalog.category_b.id)) == []  # other org: silently empty
    assert ids(brand=str(uuid.uuid4())) == []


@pytest.mark.parametrize(
    ("params", "field"),
    [({"category": "x"}, "category"), ({"brand": "1"}, "brand"), ({"q": "x" * 101}, "q")],
)
def test_invalid_product_filters_are_validation_errors(
    catalog: CatalogWorld, params: dict[str, str], field: str
) -> None:
    response = _get(_client(), "/catalog/products", **params)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert set(data["field_errors"]) == {field}


# --- Variants ---------------------------------------------------------------------


@pytest.mark.parametrize("role", ["guest", "customer"])
def test_variant_detail_is_public_representation(
    world: World, catalog: CatalogWorld, role: str
) -> None:
    client = _client(world.customer_a if role == "customer" else None)
    response = _get(client, f"/catalog/variants/{catalog.variant.id}")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == PUBLIC_VARIANT_DETAIL_KEYS
    assert set(data["product"]) == PUBLIC_VARIANT_PRODUCT_KEYS
    assert data["product"]["id"] == str(catalog.product.id)
    assert [m["id"] for m in data["media"]] == [str(catalog.variant_media_approved.id)]
    assert [a["code"] for a in data["attributes"]] == ["longitud"]
    _assert_public_payload(response)


@pytest.mark.parametrize("role", ["guest", "customer", "employee_a1"])
def test_hidden_variants_are_404_identical_to_nonexistent(
    world: World, catalog: CatalogWorld, role: str
) -> None:
    user = {"guest": None, "customer": world.customer_a, "employee_a1": world.employee_a1}[role]
    client = _client(user)
    for hidden in (
        catalog.variant_draft.id,
        catalog.variant_archived.id,
        catalog.variant_of_draft_product.id,  # published variant of a draft product
        catalog.variant_b.id,
        "not-a-uuid",
    ):
        _assert_same_as_nonexistent(client, "/catalog/variants", hidden)


def test_variant_sku_lookup_is_exact_after_trim_and_uppercase(
    world: World, catalog: CatalogWorld
) -> None:
    client = _client()

    def skus(sku: str) -> list[str]:
        response = _get(client, "/catalog/variants", sku=sku)
        assert response.status_code == 200
        data = response.json()
        assert set(data) == PAGE_KEYS
        for row in data["results"]:
            assert set(row) == PUBLIC_VARIANT_DETAIL_KEYS
        return [row["id"] for row in data["results"]]

    expected = [str(catalog.variant.id)]
    assert skus(SHARED_SKU) == expected  # org_b's variant with the same SKU is not returned
    assert skus("sin-a-001") == expected
    assert skus(f"  {SHARED_SKU}\t") == expected
    assert skus("SIN-A") == []  # no partial match
    assert skus("SIN-A-0011") == []
    assert skus("SIN-A-DRAFT") == []
    assert skus("SIN-A-ARCH") == []
    assert skus("SIN-A-DRAFTPROD") == []

    other_org = _client(world.employee_b1)
    response = _get(other_org, "/catalog/variants", sku=SHARED_SKU)
    assert [row["id"] for row in response.json()["results"]] == [str(catalog.variant_b.id)]


@pytest.mark.parametrize("params", [{}, {"sku": ""}, {"sku": "X" * 65}])
def test_variant_list_requires_valid_sku(catalog: CatalogWorld, params: dict[str, str]) -> None:
    response = _get(_client(), "/catalog/variants", **params)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert set(data["field_errors"]) == {"sku"}


# --- Pagination -------------------------------------------------------------------


def test_public_cursor_ordering_uses_only_public_fields() -> None:
    assert PRODUCT_ORDERING == ("name", "id")
    assert VARIANT_ORDERING == ("sku", "id")
    assert set(PRODUCT_ORDERING) <= PUBLIC_PRODUCT_KEYS
    assert set(VARIANT_ORDERING) <= PUBLIC_VARIANT_KEYS


def test_product_pagination_is_deterministic_and_ends_with_id(world: World) -> None:
    same = [cf.make_product(world.org_a, "Mismo nombre SINTÉTICO") for _ in range(5)]
    first = cf.make_product(world.org_a, "A primero SINTÉTICO")
    cf.make_product(world.org_a, "A borrador oculto SINTÉTICO", status=CatalogStatus.DRAFT)
    expected = [str(first.id), *sorted(str(p.id) for p in same)]
    client = _client()

    seen: list[str] = []
    cursor: str | None = None
    pages = 0
    while True:
        params: dict[str, Any] = {"page_size": 2}
        if cursor:
            params["cursor"] = cursor
        data = _get(client, "/catalog/products", **params).json()
        seen += [row["id"] for row in data["results"]]
        pages += 1
        if data["next_cursor"]:
            # Cursors are signed, not encrypted: they must hold public values only.
            payload = signing.loads(data["next_cursor"], salt=CURSOR_SALT)
            last = data["results"][-1]
            assert payload["v"] == [last["name"], last["id"]]
        cursor = data["next_cursor"]
        if not cursor:
            break
    assert pages == 3
    assert seen == expected

    # Walking back from the last page returns the same order.
    back = _get(client, "/catalog/products", page_size=2, cursor=data["previous_cursor"]).json()
    assert [row["id"] for row in back["results"]] == expected[2:4]


def test_catalog_endpoints_are_read_only(catalog: CatalogWorld) -> None:
    client = _client()
    for path in (
        "/catalog/products",
        f"/catalog/products/{catalog.product.id}",
        "/catalog/variants",
        f"/catalog/variants/{catalog.variant.id}",
    ):
        for method in (client.post, client.put, client.patch, client.delete):
            response = method(f"{API}{path}", {}, content_type="application/json")
            assert response.status_code == 405, (path, method)
            assert response.json()["code"] == "METHOD_NOT_ALLOWED"


def test_no_price_or_availability_endpoints(catalog: CatalogWorld) -> None:
    client = _client()
    for path in ("/catalog/prices", "/inventory/availability", "/catalog/availability"):
        response = _get(client, path)
        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"


def test_query_count_does_not_grow_with_rows(
    world: World, catalog: CatalogWorld, django_assert_max_num_queries: Any
) -> None:
    client = _client()
    for index in range(10):
        product = cf.make_product(world.org_a, f"Producto extra {index} SINTÉTICO")
        cf.make_media(product, f"/catalog-media/sintetico/extra-{index}.svg")
        cf.make_variant(catalog.product, f"SIN-A-EXTRA-{index}")
    # Default organization, products, media.
    with django_assert_max_num_queries(3):
        assert len(_get(client, "/catalog/products").json()["results"]) == 11
    # Default organization, product, media, attributes, variants, variant media/attributes.
    with django_assert_max_num_queries(7):
        detail = _get(client, f"/catalog/products/{catalog.product.id}").json()
    assert len(detail["variants"]) == 11
