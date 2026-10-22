from typing import Any

import pytest
from django.test import Client

from tests.fixtures import API, World, csrf_client, login


def _assert_no_store(response: Any) -> None:
    assert response["Cache-Control"] == "private, no-store"
    assert "Cookie" in response["Vary"]


@pytest.mark.django_db
def test_authenticated_responses_are_private_no_store(world: World, password: str) -> None:
    client = csrf_client()
    response = login(client, world.employee_a1.email, password)
    _assert_no_store(response)
    for path in ("/auth/me", "/branches", f"/branches/{world.a1.id}", "/health"):
        _assert_no_store(client.get(f"{API}{path}"))


@pytest.mark.django_db
def test_error_responses_for_authenticated_users_are_no_store(world: World) -> None:
    client = Client()
    client.force_login(world.admin_a)
    _assert_no_store(client.get(f"{API}/branches/{world.b1.id}"))
    _assert_no_store(client.get(f"{API}/no-existe"))


def test_csrf_bootstrap_is_no_store() -> None:
    _assert_no_store(Client().get(f"{API}/auth/csrf"))


def test_anonymous_cookieless_response_varies_on_cookie() -> None:
    response = Client().get(f"{API}/health")
    assert "Cookie" in response["Vary"]
    assert "no-store" not in response.get("Cache-Control", "")
