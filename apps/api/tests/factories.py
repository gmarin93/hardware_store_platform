"""Synthetic test factories (ADR 0001 synthetic fixtures).

Every organization is ``is_synthetic=True`` with a fictitious name; every email
uses the reserved ``example.test`` domain. Passwords are generated per test
run and never committed.
"""

import secrets
from typing import Any

from accounts.models import CustomerProfile, User
from organizations.models import Branch, BranchMembership, Organization, RoleAssignment


def generate_password() -> str:
    return secrets.token_urlsafe(18)


def make_organization(slug: str, name: str | None = None, **extra: Any) -> Organization:
    extra.setdefault("is_synthetic", True)
    return Organization.objects.create(
        slug=slug, name=name or f"Ferretería Ficticia {slug} (SINTÉTICO)", **extra
    )


def make_branch(organization: Organization, code: str, **extra: Any) -> Branch:
    extra.setdefault("name", f"Sucursal {code} (SINTÉTICO)")
    return Branch.objects.create(organization=organization, code=code, **extra)


def make_user(local_part: str, password: str | None = None, **extra: Any) -> User:
    extra.setdefault("full_name", f"Persona Ficticia {local_part}")
    return User.objects.create_user(f"{local_part}@example.test", password, **extra)


def make_employee(
    local_part: str, branches: list[Branch], password: str | None = None, **extra: Any
) -> User:
    user = make_user(local_part, password, **extra)
    for branch in branches:
        BranchMembership.objects.create(user=user, branch=branch)
    return user


def make_admin(
    local_part: str, organization: Organization, password: str | None = None, **extra: Any
) -> User:
    user = make_user(local_part, password, **extra)
    RoleAssignment.objects.create(
        user=user, organization=organization, role=RoleAssignment.RoleName.ADMIN
    )
    return user


def make_customer(
    local_part: str, organization: Organization, password: str | None = None, **extra: Any
) -> User:
    user = make_user(local_part, password, **extra)
    CustomerProfile.objects.create(user=user, organization=organization)
    return user
