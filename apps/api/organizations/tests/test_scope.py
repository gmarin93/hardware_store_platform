import uuid
from typing import Any

import pytest
from django.conf import settings
from django.test import Client
from rest_framework.exceptions import NotFound

from accounts.models import User
from accounts.permissions import ROLE_PERMISSIONS, Perm, Role
from organizations.models import BranchMembership, Organization, RoleAssignment
from organizations.scope import get_visible_branch, resolve_actor, visible_branches
from organizations.tests.probe_urls import PROBE_PATH
from tests.fixtures import API, World, csrf_client, login

pytestmark = pytest.mark.django_db

SAME_REQUEST_ID = "scope-404-check"


def _client_for(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def _branch_ids(client: Client) -> list[str]:
    response = client.get(f"{API}/branches")
    assert response.status_code == 200
    return [row["id"] for row in response.json()["results"]]


def _detail(client: Client, branch_id: object) -> Any:
    return client.get(f"{API}/branches/{branch_id}", headers={"X-Request-ID": SAME_REQUEST_ID})


def _assert_same_as_nonexistent(client: Client, branch_id: object) -> None:
    hidden = _detail(client, branch_id)
    missing = _detail(client, uuid.uuid4())
    assert hidden.status_code == missing.status_code == 404
    assert hidden.content == missing.content
    assert dict(hidden.headers) == dict(missing.headers)
    assert hidden.json() == {
        "code": "NOT_FOUND",
        "message": "El recurso solicitado no existe.",
        "field_errors": {},
        "request_id": SAME_REQUEST_ID,
    }


# --- Fixture sanity: two synthetic organizations -------------------------------


def test_fixtures_are_synthetic(world: World) -> None:
    assert Organization.objects.count() == 2
    assert all(org.is_synthetic for org in Organization.objects.all())
    assert all(u.email.endswith("@example.test") for u in User.objects.all())
    assert world.org_a.slug == settings.DEFAULT_ORGANIZATION_SLUG


# --- EMPLOYEE ---------------------------------------------------------------------


def test_employee_sees_only_active_member_branches(world: World) -> None:
    assert _branch_ids(_client_for(world.employee_a1)) == [str(world.a1.id)]
    assert sorted(_branch_ids(_client_for(world.employee_a12))) == sorted(
        [str(world.a1.id), str(world.a2.id)]
    )


def test_employee_non_member_and_cross_org_branches_are_404(world: World) -> None:
    client = _client_for(world.employee_a1)
    assert _detail(client, world.a1.id).status_code == 200
    _assert_same_as_nonexistent(client, world.a2.id)  # same org, not a member
    _assert_same_as_nonexistent(client, world.a_inactive.id)  # member, branch inactive
    _assert_same_as_nonexistent(client, world.b1.id)  # other organization


def test_revoked_membership_grants_nothing(world: World) -> None:
    client = _client_for(world.employee_revoked)
    assert _branch_ids(client) == []
    _assert_same_as_nonexistent(client, world.a2.id)
    me = client.get(f"{API}/auth/me").json()
    assert me["role"] == "GUEST"
    assert me["permissions"] == ["catalog.view_published"]


def test_membership_revoked_during_session_is_denied_on_next_request(
    world: World, password: str
) -> None:
    client = csrf_client()
    assert login(client, world.employee_a1.email, password).status_code == 200
    assert _detail(client, world.a1.id).status_code == 200

    BranchMembership.objects.filter(user=world.employee_a1).update(is_active=False)

    _assert_same_as_nonexistent(client, world.a1.id)
    assert _branch_ids(client) == []


def test_admin_assignment_revoked_during_session(world: World) -> None:
    client = _client_for(world.admin_a)
    assert len(_branch_ids(client)) == 2

    RoleAssignment.objects.filter(user=world.admin_a).update(is_active=False)

    assert _branch_ids(client) == []
    assert client.get(f"{API}/auth/me").json()["role"] == "GUEST"


# --- ADMIN ------------------------------------------------------------------------


def test_admin_sees_all_active_branches_of_own_org_only(world: World) -> None:
    client = _client_for(world.admin_a)
    assert sorted(_branch_ids(client)) == sorted([str(world.a1.id), str(world.a2.id)])
    _assert_same_as_nonexistent(client, world.b1.id)

    other = _client_for(world.admin_b)
    assert _branch_ids(other) == [str(world.b1.id)]
    _assert_same_as_nonexistent(other, world.a1.id)


def test_inactive_organization_grants_nothing(world: World) -> None:
    Organization.objects.filter(pk=world.org_b.pk).update(is_active=False)
    assert _branch_ids(_client_for(world.admin_b)) == []
    assert _branch_ids(_client_for(world.employee_b1)) == []


# --- CUSTOMER / GUEST / superuser / misconfigured ---------------------------------


def test_customer_sees_no_branch_staff_data(world: World) -> None:
    client = _client_for(world.customer_a)
    assert _branch_ids(client) == []
    _assert_same_as_nonexistent(client, world.a1.id)
    me = client.get(f"{API}/auth/me").json()
    assert me["role"] == "CUSTOMER"
    assert me["organization"]["id"] == str(world.org_a.id)
    assert me["branches"] == []
    assert Perm.CATALOG_VIEW_STAFF_FIELDS not in me["permissions"]


def test_guest_only_reaches_public_endpoints(world: World) -> None:
    client = Client()
    assert client.get(f"{API}/health").status_code == 200
    assert client.get(f"{API}/auth/csrf").status_code == 204
    for path in ("/branches", f"/branches/{world.a1.id}", "/auth/me"):
        response = client.get(f"{API}{path}")
        assert response.status_code == 401, path
        assert response.json()["code"] == "NOT_AUTHENTICATED"

    guest = resolve_actor(None)
    assert guest.role is Role.GUEST
    assert guest.organization == world.org_a  # DEFAULT_ORGANIZATION_SLUG
    assert guest.permissions == frozenset({Perm.CATALOG_VIEW_PUBLISHED})
    assert not visible_branches(guest).exists()


@pytest.mark.parametrize("attr", ["superuser", "no_role", "ambiguous"])
def test_superuser_and_roleless_accounts_get_nothing(world: World, attr: str) -> None:
    user = getattr(world, attr)
    client = _client_for(user)
    assert _branch_ids(client) == []
    for branch in (world.a1, world.b1):
        _assert_same_as_nonexistent(client, branch.id)
    me = client.get(f"{API}/auth/me").json()
    assert me["role"] == "GUEST"
    assert me["branches"] == []
    assert me["permissions"] == ["catalog.view_published"]


@pytest.mark.parametrize(
    ("attr", "role"),
    [
        ("admin_a", Role.ADMIN),
        ("employee_a12", Role.EMPLOYEE),
        ("customer_a", Role.CUSTOMER),
    ],
)
def test_me_reports_role_and_effective_permissions(world: World, attr: str, role: Role) -> None:
    me = _client_for(getattr(world, attr)).get(f"{API}/auth/me").json()
    assert me["role"] == role.value
    assert me["permissions"] == sorted(str(p) for p in ROLE_PERMISSIONS[role])


# --- Forged selectors ----------------------------------------------------------------


@pytest.mark.parametrize(
    "forged", ["not-a-uuid", "", None, 42, "00000000-0000-0000-0000-000000000000"]
)
def test_selector_rejects_malformed_or_unknown_ids(world: World, forged: object) -> None:
    actor = resolve_actor(world.admin_a)
    with pytest.raises(NotFound):
        get_visible_branch(actor, forged)


def test_forged_branch_id_grants_nothing(world: World) -> None:
    employee = resolve_actor(world.employee_a1)
    assert get_visible_branch(employee, str(world.a1.id)) == world.a1
    for forged in (world.a2.id, str(world.b1.id), world.a_inactive.id):
        with pytest.raises(NotFound):
            get_visible_branch(employee, forged)


def test_malformed_path_id_is_same_404_as_missing(world: World) -> None:
    client = _client_for(world.admin_a)
    for bad in ("not-a-uuid", "123", "%00", "' OR 1=1"):
        malformed = _detail(client, bad)
        missing = _detail(client, uuid.uuid4())
        assert malformed.status_code == 404, bad
        assert malformed.content == missing.content
        assert dict(malformed.headers) == dict(missing.headers)


# --- Visible but forbidden (403) vs invisible (404) ------------------------------------


@pytest.mark.urls("organizations.tests.probe_urls")
def test_visible_but_forbidden_action_is_403(world: World, password: str) -> None:
    def post(user: User | None, branch_id: object) -> Any:
        client = csrf_client()
        token = ""
        if user is not None:
            assert login(client, user.email, password).status_code == 200
            token = str(client.cookies[settings.CSRF_COOKIE_NAME].value)
        return client.post(
            PROBE_PATH.format(branch_id),
            {},
            content_type="application/json",
            headers={"X-CSRFToken": token} if token else {},
        )

    forbidden = post(world.employee_a1, world.a1.id)
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "PERMISSION_DENIED"
    assert forbidden.json()["message"] == "No tiene permiso para realizar esta acción."

    assert post(world.admin_a, world.a1.id).status_code == 204
    assert post(world.employee_a1, world.a2.id).json()["code"] == "NOT_FOUND"
    assert post(world.admin_b, world.a1.id).json()["code"] == "NOT_FOUND"
    assert post(world.superuser, world.a1.id).json()["code"] == "NOT_FOUND"
    assert post(None, world.a1.id).status_code == 401


@pytest.mark.urls("organizations.tests.probe_urls")
def test_unsafe_authenticated_request_requires_csrf(world: World, password: str) -> None:
    client = csrf_client()
    assert login(client, world.admin_a.email, password).status_code == 200

    response = client.post(PROBE_PATH.format(world.a1.id), {}, content_type="application/json")

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_FAILED"

    token = str(client.cookies[settings.CSRF_COOKIE_NAME].value)
    foreign = client.post(
        PROBE_PATH.format(world.a1.id),
        {},
        content_type="application/json",
        headers={"X-CSRFToken": token, "Origin": "http://evil.example.test"},
    )
    assert foreign.status_code == 403
    assert foreign.json()["code"] == "CSRF_FAILED"

    accepted = client.post(
        PROBE_PATH.format(world.a1.id),
        {},
        content_type="application/json",
        headers={"X-CSRFToken": token, "Origin": "http://testserver"},
    )
    assert accepted.status_code == 204


# --- Permission table ---------------------------------------------------------------------


def test_role_permission_table_invariants() -> None:
    guest, customer, employee, admin = (ROLE_PERMISSIONS[r] for r in Role)
    assert guest == {Perm.CATALOG_VIEW_PUBLISHED}
    assert guest < customer and guest < employee and guest < admin
    assert Perm.CATALOG_VIEW_STAFF_FIELDS not in customer
    assert employee - {Perm.BRANCHES_VIEW_ASSIGNED} <= admin
    admin_only = {
        Perm.INVENTORY_ADJUST,
        Perm.PRICING_MANAGE,
        Perm.STAFF_MANAGE,
        Perm.AUDIT_VIEW,
        Perm.BRANCHES_VIEW_ALL,
    }
    assert admin_only <= admin
    assert not admin_only & (employee | customer)
