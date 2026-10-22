from typing import Any

import pytest
from django.test import Client

from common.pagination import CursorPagination, validate_ordering
from organizations.models import Branch
from tests.factories import make_admin, make_branch, make_organization
from tests.fixtures import API

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client() -> tuple[Client, list[str]]:
    org = make_organization("paginacion-sintetica")
    other = make_organization("otra-paginacion-sintetica")
    make_branch(other, "ajena", name="Sucursal")
    # Identical names force the id tiebreak.
    ids = [str(make_branch(org, f"s{i:03d}", name="Sucursal").id) for i in range(45)]
    client = Client()
    client.force_login(make_admin("admin.paginacion", org))
    return client, sorted(ids)


def _get(client: Client, **params: Any) -> Any:
    response = client.get(f"{API}/branches", params)
    assert response.status_code == 200, response.content
    return response.json()


def test_walks_forward_and_backward_without_gaps(admin_client: tuple[Client, list[str]]) -> None:
    client, expected = admin_client
    pages = []
    body = _get(client)
    assert set(body) == {"results", "next_cursor", "previous_cursor"}
    assert body["previous_cursor"] is None
    assert len(body["results"]) == 20
    pages.append(body)
    while body["next_cursor"]:
        body = _get(client, cursor=body["next_cursor"])
        pages.append(body)

    assert [len(p["results"]) for p in pages] == [20, 20, 5]
    seen = [row["id"] for p in pages for row in p["results"]]
    assert seen == expected  # name tie -> ordered by id, no duplicates or gaps
    assert pages[-1]["next_cursor"] is None

    back = _get(client, cursor=pages[-1]["previous_cursor"])
    assert [r["id"] for r in back["results"]] == expected[20:40]
    back = _get(client, cursor=back["previous_cursor"])
    assert [r["id"] for r in back["results"]] == expected[:20]
    assert back["previous_cursor"] is None
    assert back["next_cursor"]


def test_page_size_is_bounded(admin_client: tuple[Client, list[str]]) -> None:
    client, _ = admin_client
    assert len(_get(client, page_size=7)["results"]) == 7
    org = Branch.objects.get(code="s000").organization
    for i in range(60):
        make_branch(org, f"x{i:03d}")
    assert len(_get(client, page_size=500)["results"]) == 100


@pytest.mark.parametrize("value", ["0", "-1", "abc", "1.5"])
def test_invalid_page_size_is_validation_error(
    admin_client: tuple[Client, list[str]], value: str
) -> None:
    client, _ = admin_client
    response = client.get(f"{API}/branches", {"page_size": value})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert set(response.json()["field_errors"]) == {"page_size"}


@pytest.mark.parametrize("cursor", ["garbage", "eyJ2IjpbXX0:abc:def"])
def test_tampered_cursor_is_rejected(admin_client: tuple[Client, list[str]], cursor: str) -> None:
    client, _ = admin_client
    response = client.get(f"{API}/branches", {"cursor": cursor})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_CURSOR"


def test_cursor_is_opaque_and_carries_no_scope(admin_client: tuple[Client, list[str]]) -> None:
    client, _ = admin_client
    cursor = _get(client)["next_cursor"]
    assert "Sucursal" not in cursor
    # A cursor reused by an actor with no branches yields nothing extra.
    outsider = Client()
    outsider.force_login(make_admin("admin.ajeno", make_organization("ajena-sintetica")))
    assert _get(outsider, cursor=cursor)["results"] == []


def test_ordering_must_end_with_id() -> None:
    assert validate_ordering(("name", "id")) == ("name", "id")
    assert validate_ordering(("-created_at", "-id")) == ("-created_at", "-id")
    for bad in [(), ("name",), ("id", "name"), ("branch__name", "id")]:
        with pytest.raises(ValueError):
            validate_ordering(bad)
    assert CursorPagination.page_size == 20
    assert CursorPagination.max_page_size == 100
