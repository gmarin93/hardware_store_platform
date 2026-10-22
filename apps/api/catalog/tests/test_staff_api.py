"""Staff catalog API (``/catalog/staff/...``): EMPLOYEE/ADMIN of the organization only."""

import uuid
from typing import Any

import pytest
from django.test import Client

from accounts.models import User
from catalog.tests.fixtures import SHARED_SKU, CatalogWorld
from catalog.tests.keys import (
    SOURCE_KEYS,
    STAFF_ATTRIBUTE_KEYS,
    STAFF_MEDIA_KEYS,
    STAFF_PRODUCT_DETAIL_KEYS,
    STAFF_PRODUCT_KEYS,
    STAFF_VARIANT_DETAIL_KEYS,
    STAFF_VARIANT_KEYS,
    STAFF_VARIANT_PRODUCT_KEYS,
)
from organizations.models import BranchMembership
from tests.fixtures import API, World, csrf_client, login

pytestmark = pytest.mark.django_db

SAME_REQUEST_ID = "catalog-staff-404-check"


def _client(user: User | None = None) -> Client:
    client = Client()
    if user is not None:
        client.force_login(user)
    return client


def _get(client: Client, path: str, **params: Any) -> Any:
    return client.get(f"{API}{path}", params, headers={"X-Request-ID": SAME_REQUEST_ID})


def _staff_paths(catalog: CatalogWorld) -> list[tuple[str, dict[str, str]]]:
    return [
        ("/catalog/staff/products", {}),
        (f"/catalog/staff/products/{catalog.product.id}", {}),
        (f"/catalog/staff/products/{uuid.uuid4()}", {}),
        ("/catalog/staff/variants", {"sku": SHARED_SKU}),
        (f"/catalog/staff/variants/{catalog.variant.id}", {}),
        (f"/catalog/staff/variants/{uuid.uuid4()}", {}),
    ]


def test_anonymous_gets_401_on_every_staff_endpoint(catalog: CatalogWorld) -> None:
    client = _client()
    for path, params in _staff_paths(catalog):
        response = _get(client, path, **params)
        assert response.status_code == 401, path
        assert response.json()["code"] == "NOT_AUTHENTICATED"
        assert response.headers["WWW-Authenticate"] == "Session"


@pytest.mark.parametrize("role", ["customer_a", "no_role", "superuser", "employee_revoked"])
def test_non_staff_accounts_get_403_independent_of_the_id(
    world: World, catalog: CatalogWorld, role: str
) -> None:
    client = _client(getattr(world, role))
    bodies = set()
    for path, params in _staff_paths(catalog):
        response = _get(client, path, **params)
        assert response.status_code == 403, path
        assert response.json()["code"] == "PERMISSION_DENIED"
        bodies.add(response.content)
    # Existing and nonexistent ids give the same answer: no existence oracle.
    assert len(bodies) == 1


@pytest.mark.parametrize("role", ["employee_a1", "admin_a"])
def test_staff_list_includes_every_status_of_own_org_only(
    world: World, catalog: CatalogWorld, role: str
) -> None:
    response = _get(_client(getattr(world, role)), "/catalog/staff/products")
    assert response.status_code == 200
    rows = response.json()["results"]
    assert {row["id"] for row in rows} == {
        str(catalog.product.id),
        str(catalog.product_draft.id),
        str(catalog.product_archived.id),
    }
    for row in rows:
        assert set(row) == STAFF_PRODUCT_KEYS
    statuses = {row["id"]: row["status"] for row in rows}
    assert statuses[str(catalog.product_draft.id)] == "DRAFT"
    assert statuses[str(catalog.product_archived.id)] == "ARCHIVED"
    published = next(row for row in rows if row["id"] == str(catalog.product.id))
    assert [m["status"] for m in published["media"]] == ["APPROVED", "DRAFT"]


def test_staff_list_status_filter(world: World, catalog: CatalogWorld) -> None:
    client = _client(world.admin_a)
    rows = _get(client, "/catalog/staff/products", status="DRAFT").json()["results"]
    assert [row["id"] for row in rows] == [str(catalog.product_draft.id)]
    response = _get(client, "/catalog/staff/products", status="BORRADOR")
    assert response.status_code == 400
    assert set(response.json()["field_errors"]) == {"status"}


def test_staff_product_detail_has_staff_fields(world: World, catalog: CatalogWorld) -> None:
    response = _get(_client(world.employee_a1), f"/catalog/staff/products/{catalog.product.id}")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == STAFF_PRODUCT_DETAIL_KEYS
    assert data["internal_notes"] == "NOTA-INTERNA-PRODUCTO"
    assert {v["sku"] for v in data["variants"]} == {SHARED_SKU, "SIN-A-DRAFT", "SIN-A-ARCH"}
    for variant in data["variants"]:
        assert set(variant) == STAFF_VARIANT_KEYS
    assert {a["code"]: a["is_published"] for a in data["attributes"]} == {
        "material": True,
        "nota-oculta": False,
        "uso-exterior": True,
    }
    for attribute in data["attributes"]:
        assert set(attribute) == STAFF_ATTRIBUTE_KEYS
    for media in data["media"]:
        assert set(media) == STAFF_MEDIA_KEYS
    assert [s["external_id"] for s in data["source_references"]] == ["PROD-1"]
    assert set(data["source_references"][0]) == SOURCE_KEYS
    assert data["source_references"][0]["is_synthetic"] is True


def test_staff_variant_detail_and_sku_lookup(world: World, catalog: CatalogWorld) -> None:
    client = _client(world.admin_a)
    response = _get(client, f"/catalog/staff/variants/{catalog.variant.id}")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == STAFF_VARIANT_DETAIL_KEYS
    assert set(data["product"]) == STAFF_VARIANT_PRODUCT_KEYS
    assert data["supplier_code"] == "PROV-OCULTO-1"
    assert data["stock_unit"] == data["sales_unit"] == "piece"
    assert [s["external_id"] for s in data["source_references"]] == ["VAR-1"]
    assert sorted(m["status"] for m in data["media"]) == ["APPROVED", "DRAFT"]

    for hidden in (catalog.variant_draft, catalog.variant_of_draft_product):
        response = _get(client, f"/catalog/staff/variants/{hidden.id}")
        assert response.status_code == 200
        rows = _get(client, "/catalog/staff/variants", sku=hidden.sku.lower()).json()["results"]
        assert [row["id"] for row in rows] == [str(hidden.id)]
    response = _get(client, f"/catalog/staff/products/{catalog.product_draft.id}")
    assert response.json()["status"] == "DRAFT"


@pytest.mark.parametrize("role", ["admin_b", "employee_b1"])
def test_staff_of_other_org_never_sees_org_a(
    world: World, catalog: CatalogWorld, role: str
) -> None:
    client = _client(getattr(world, role))
    rows = _get(client, "/catalog/staff/products").json()["results"]
    assert [row["id"] for row in rows] == [str(catalog.product_b.id)]
    rows = _get(client, "/catalog/staff/variants", sku=SHARED_SKU).json()["results"]
    assert [row["id"] for row in rows] == [str(catalog.variant_b.id)]
    for prefix, hidden_id in (
        ("/catalog/staff/products", catalog.product.id),
        ("/catalog/staff/products", catalog.product_draft.id),
        ("/catalog/staff/variants", catalog.variant.id),
        ("/catalog/staff/variants", catalog.variant_draft.id),
        ("/catalog/staff/variants", "not-a-uuid"),
    ):
        hidden = _get(client, f"{prefix}/{hidden_id}")
        missing = _get(client, f"{prefix}/{uuid.uuid4()}")
        assert hidden.status_code == missing.status_code == 404
        assert hidden.content == missing.content
        assert dict(hidden.headers) == dict(missing.headers)


def test_revoked_membership_loses_staff_view_on_next_request(
    world: World, catalog: CatalogWorld, password: str
) -> None:
    client = csrf_client()
    assert login(client, world.employee_a1.email, password).status_code == 200
    path = f"{API}/catalog/staff/products/{catalog.product_draft.id}"
    assert client.get(path).status_code == 200
    BranchMembership.objects.filter(user=world.employee_a1).update(is_active=False)
    assert client.get(path).status_code == 403
    # The public view still works and still hides the draft.
    assert client.get(f"{API}/catalog/products/{catalog.product_draft.id}").status_code == 404


def test_staff_responses_are_not_cacheable(world: World, catalog: CatalogWorld) -> None:
    response = _get(_client(world.admin_a), "/catalog/staff/products")
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "Cookie" in response.headers["Vary"]
