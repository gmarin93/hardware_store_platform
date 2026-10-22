"""Shared pytest fixtures. Import from an app's ``tests/conftest.py``:

    from tests.fixtures import *  # noqa: F403

``world`` always builds two synthetic organizations so cross-organization
denial is tested everywhere.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import Client

from accounts.models import User
from organizations.models import Branch, BranchMembership, Organization
from tests import factories

API = "/api/v1"

__all__ = [
    "API",
    "World",
    "clear_cache",
    "csrf_client",
    "csrf_token",
    "login",
    "password",
    "world",
]


@dataclass
class World:
    org_a: Organization
    org_b: Organization
    a1: Branch
    a2: Branch
    a_inactive: Branch
    b1: Branch
    admin_a: User
    employee_a1: User
    employee_a12: User
    employee_revoked: User
    customer_a: User
    admin_b: User
    employee_b1: User
    superuser: User
    no_role: User
    ambiguous: User


@pytest.fixture(autouse=True)
def clear_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def password() -> str:
    return factories.generate_password()


@pytest.fixture
def world(db: Any, password: str) -> World:
    f = factories
    org_a = f.make_organization(settings.DEFAULT_ORGANIZATION_SLUG, "Ferretería Demo (SINTÉTICO)")
    org_b = f.make_organization("otra-ferreteria-sintetica", "Otra Ferretería (SINTÉTICO)")
    a1 = f.make_branch(org_a, "a1", name="Sucursal Norte (SINTÉTICO)")
    a2 = f.make_branch(org_a, "a2", name="Sucursal Sur (SINTÉTICO)")
    a_inactive = f.make_branch(org_a, "a-cerrada", is_active=False)
    b1 = f.make_branch(org_b, "b1")
    employee_revoked = f.make_employee("empleado.revocado", [a2], password)
    BranchMembership.objects.filter(user=employee_revoked).update(is_active=False)
    ambiguous = f.make_employee("empleado.ambiguo", [a1, b1], password)
    return World(
        org_a=org_a,
        org_b=org_b,
        a1=a1,
        a2=a2,
        a_inactive=a_inactive,
        b1=b1,
        admin_a=f.make_admin("admin.a", org_a, password),
        employee_a1=f.make_employee("empleado.a1", [a1, a_inactive], password),
        employee_a12=f.make_employee("empleado.a12", [a1, a2], password),
        employee_revoked=employee_revoked,
        customer_a=f.make_customer("cliente.a", org_a, password),
        admin_b=f.make_admin("admin.b", org_b, password),
        employee_b1=f.make_employee("empleado.b1", [b1], password),
        superuser=User.objects.create_superuser("super@example.test", password),
        no_role=f.make_user("sin.rol", password),
        ambiguous=ambiguous,
    )


def csrf_client() -> Client:
    """A client that enforces CSRF exactly like a browser request would."""
    return Client(enforce_csrf_checks=True)


def csrf_token(client: Client) -> str:
    response = client.get(f"{API}/auth/csrf")
    assert response.status_code == 204
    return str(client.cookies[settings.CSRF_COOKIE_NAME].value)


def login(client: Client, email: str, password: str) -> Any:
    token = csrf_token(client)
    return client.post(
        f"{API}/auth/login",
        {"email": email, "password": password},
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
