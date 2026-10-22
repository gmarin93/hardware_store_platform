import pytest
from django.db import connection
from django.test import Client

from config import health


@pytest.mark.django_db
def test_health_reports_database_ok_against_postgres(client: Client) -> None:
    assert connection.vendor == "postgresql"

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_unavailable_without_details(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health, "database_is_reachable", lambda: False)

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unreachable"}


@pytest.mark.parametrize("path", ["/admin/", "/admin/login/", "/api/v1/admin/"])
def test_django_admin_is_not_mounted(client: Client, path: str) -> None:
    assert client.get(path).status_code == 404
