import logging
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.test import Client, RequestFactory, override_settings

from accounts.models import User
from common.client_ip import client_ip
from tests.factories import make_user
from tests.fixtures import API, World, csrf_client, csrf_token, login

pytestmark = pytest.mark.django_db

FOREIGN_ORIGIN = "http://evil.example.test"


def _post(client: Client, path: str, data: object = None, **headers: str) -> Any:
    return client.post(f"{API}{path}", data or {}, content_type="application/json", headers=headers)


def _session_key(client: Client) -> str:
    return str(client.cookies[settings.SESSION_COOKIE_NAME].value)


# --- CSRF bootstrap, login, logout, me --------------------------------------


def test_csrf_endpoint_sets_readable_cookie() -> None:
    client = csrf_client()
    response = client.get(f"{API}/auth/csrf")

    assert response.status_code == 204
    cookie = client.cookies[settings.CSRF_COOKIE_NAME]
    assert cookie.value
    assert not cookie["httponly"]
    assert cookie["samesite"] == "Lax"


def test_login_returns_me_payload_and_rotates_session_key(world: World, password: str) -> None:
    client = csrf_client()
    anonymous_session = client.session  # creates and stores a pre-login session
    anonymous_session["probe"] = "x"
    anonymous_session.save()
    old_key = _session_key(client)
    pre_login_token = csrf_token(client)

    response = login(client, world.employee_a1.email, password)

    assert response.status_code == 200
    body = response.json()
    assert body["user"] == {
        "id": str(world.employee_a1.id),
        "email": world.employee_a1.email,
        "full_name": world.employee_a1.full_name,
    }
    assert body["role"] == "EMPLOYEE"
    assert body["organization"]["id"] == str(world.org_a.id)
    assert body["organization"]["is_synthetic"] is True
    assert [b["id"] for b in body["branches"]] == [str(world.a1.id)]
    assert "password" not in response.content.decode()
    new_key = _session_key(client)
    assert new_key != old_key
    assert str(client.cookies[settings.CSRF_COOKIE_NAME].value) != pre_login_token
    assert not Session.objects.filter(session_key=old_key).exists()
    cookie = client.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"


def test_pre_login_csrf_token_is_rejected_after_login(world: World, password: str) -> None:
    client = csrf_client()
    pre_login_token = csrf_token(client)
    response = client.post(
        f"{API}/auth/login",
        {"email": world.employee_a1.email, "password": password},
        content_type="application/json",
        headers={"X-CSRFToken": pre_login_token},
    )
    assert response.status_code == 200
    rotated = str(client.cookies[settings.CSRF_COOKIE_NAME].value)
    assert rotated != pre_login_token

    stale = _post(client, "/auth/logout", **{"X-CSRFToken": pre_login_token})
    assert stale.json()["code"] == "CSRF_FAILED"
    assert _post(client, "/auth/logout", **{"X-CSRFToken": rotated}).status_code == 204


def test_login_email_is_case_insensitive(world: World, password: str) -> None:
    response = login(csrf_client(), "  ADMIN.A@Example.Test ", password)

    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_logout_flushes_session(world: World, password: str) -> None:
    client = csrf_client()
    assert login(client, world.employee_a1.email, password).status_code == 200
    key = _session_key(client)
    token = str(client.cookies[settings.CSRF_COOKIE_NAME].value)

    response = _post(client, "/auth/logout", **{"X-CSRFToken": token})

    assert response.status_code == 204
    assert response["Cache-Control"] == "private, no-store"
    assert not Session.objects.filter(session_key=key).exists()
    assert client.get(f"{API}/auth/me").status_code == 401


def test_logout_get_is_method_not_allowed(world: World) -> None:
    client = Client()
    client.force_login(world.employee_a1)

    response = client.get(f"{API}/auth/logout")

    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"
    assert "POST" in response["Allow"]
    assert client.get(f"{API}/auth/me").status_code == 200


def test_me_requires_authentication_with_401() -> None:
    response = Client().get(f"{API}/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"
    assert response["WWW-Authenticate"] == "Session"


# --- CSRF negatives ------------------------------------------------------------


def test_login_without_csrf_token_is_rejected(world: World, password: str) -> None:
    client = csrf_client()
    csrf_token(client)  # cookie present, header missing

    response = _post(
        client, "/auth/login", {"email": world.employee_a1.email, "password": password}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_FAILED"
    assert settings.SESSION_COOKIE_NAME not in client.cookies


def test_login_without_any_csrf_cookie_is_rejected(world: World, password: str) -> None:
    response = _post(
        csrf_client(), "/auth/login", {"email": world.employee_a1.email, "password": password}
    )

    assert response.json()["code"] == "CSRF_FAILED"


def test_login_from_foreign_origin_is_rejected(world: World, password: str) -> None:
    client = csrf_client()
    token = csrf_token(client)

    response = _post(
        client,
        "/auth/login",
        {"email": world.employee_a1.email, "password": password},
        **{"X-CSRFToken": token, "Origin": FOREIGN_ORIGIN},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_FAILED"


@pytest.mark.parametrize("variant", ["missing", "wrong", "foreign_origin"])
def test_logout_requires_csrf_even_with_session_cookie(
    world: World, password: str, variant: str
) -> None:
    client = csrf_client()
    assert login(client, world.employee_a1.email, password).status_code == 200
    token = str(client.cookies[settings.CSRF_COOKIE_NAME].value)
    headers = {
        "missing": {},
        "wrong": {"X-CSRFToken": "x" * 32},
        "foreign_origin": {"X-CSRFToken": token, "Origin": FOREIGN_ORIGIN},
    }[variant]

    response = _post(client, "/auth/logout", **headers)

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_FAILED"
    assert client.get(f"{API}/auth/me").status_code == 200  # still logged in


def test_anonymous_logout_still_requires_csrf() -> None:
    response = _post(csrf_client(), "/auth/logout")

    assert response.json()["code"] == "CSRF_FAILED"


# --- Credentials and throttling -------------------------------------------------


def test_invalid_credentials_are_uniform(world: World, password: str) -> None:
    inactive = make_user("inactivo", password, is_active=False)
    no_password = make_user("sin.clave")
    request_id = "uniform-check"
    bodies = []
    for email, pw in [
        ("nadie@example.test", password),
        (world.employee_a1.email, password + "x"),
        (inactive.email, password),
        (no_password.email, ""),
        (no_password.email, "anything-at-all"),
    ]:
        client = csrf_client()
        token = csrf_token(client)
        response = client.post(
            f"{API}/auth/login",
            {"email": email, "password": pw},
            content_type="application/json",
            headers={"X-CSRFToken": token, "X-Request-ID": request_id},
        )
        if pw == "":
            # Blank password is a validation error before authentication.
            assert response.status_code == 400
            assert response.json()["code"] == "VALIDATION_ERROR"
            continue
        assert response.status_code == 400
        assert settings.SESSION_COOKIE_NAME not in client.cookies
        bodies.append(response.content)

    assert len(set(bodies)) == 1
    assert b'"INVALID_CREDENTIALS"' in bodies[0]


def test_login_is_throttled_per_account(world: World, password: str) -> None:
    statuses: list[int] = []
    for _ in range(6):
        client = csrf_client()
        token = csrf_token(client)
        response = client.post(
            f"{API}/auth/login",
            {"email": world.employee_a1.email, "password": "wrong-" + password},
            content_type="application/json",
            headers={"X-CSRFToken": token},
        )
        statuses.append(response.status_code)

    assert statuses == [400] * 5 + [429]
    assert response.json()["code"] == "THROTTLED"
    assert int(response["Retry-After"]) > 0


def _ip_burst(password: str, count: int, forwarded: Callable[[int], str] | None) -> list[int]:
    """Login attempts with distinct emails, so only the per-IP limit applies."""
    client = csrf_client()
    token = csrf_token(client)
    statuses: list[int] = []
    for index in range(count):
        headers = {"X-CSRFToken": token}
        if forwarded is not None:
            headers["X-Forwarded-For"] = forwarded(index)
        response = client.post(
            f"{API}/auth/login",
            {"email": f"desconocido{index}@example.test", "password": password},
            content_type="application/json",
            headers=headers,
        )
        statuses.append(response.status_code)
    return statuses


def test_login_is_throttled_per_client_address(world: World, password: str) -> None:
    assert _ip_burst(password, 21, None) == [400] * 20 + [429]


def test_spoofed_forwarded_for_from_non_proxy_is_ignored(world: World, password: str) -> None:
    # REMOTE_ADDR 127.0.0.1 is not a trusted proxy (default TRUSTED_PROXY_HOSTS).
    assert _ip_burst(password, 21, lambda i: f"203.0.113.{i}") == [400] * 20 + [429]


@override_settings(TRUSTED_PROXY_HOSTS=["127.0.0.0/8"])
def test_forwarded_for_from_trusted_proxy_is_honoured(world: World, password: str) -> None:
    # Distinct client addresses behind the proxy have separate buckets ...
    assert 429 not in _ip_burst(password, 25, lambda i: f"203.0.113.{i}")
    cache.clear()
    # ... and the same client address behind the proxy is limited.
    assert _ip_burst(password, 21, lambda i: "198.51.100.7") == [400] * 20 + [429]


@override_settings(TRUSTED_PROXY_HOSTS=["127.0.0.1"])
def test_client_ip_rules() -> None:
    factory = RequestFactory()

    def ip(remote: str, forwarded: str | None) -> str:
        request = factory.get("/")
        request.META["REMOTE_ADDR"] = remote
        if forwarded is not None:
            request.META["HTTP_X_FORWARDED_FOR"] = forwarded
        return client_ip(request)

    assert ip("127.0.0.1", "203.0.113.5") == "203.0.113.5"
    assert ip("127.0.0.1", "1.1.1.1, 203.0.113.5") == "203.0.113.5"
    assert ip("127.0.0.1", "not-an-ip") == "127.0.0.1"
    assert ip("127.0.0.1", None) == "127.0.0.1"
    assert ip("10.9.9.9", "203.0.113.5") == "10.9.9.9"


@override_settings(TRUSTED_PROXY_HOSTS=["nonexistent-proxy.invalid"])
def test_unresolvable_proxy_name_trusts_nothing() -> None:
    request = RequestFactory().get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.5")
    assert client_ip(request) == "127.0.0.1"


def test_deactivated_user_loses_existing_session(world: World, password: str) -> None:
    client = csrf_client()
    assert login(client, world.employee_a1.email, password).status_code == 200
    assert client.get(f"{API}/auth/me").status_code == 200

    User.objects.filter(pk=world.employee_a1.pk).update(is_active=False)

    response = client.get(f"{API}/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"
    assert client.get(f"{API}/branches/{world.a1.id}").status_code == 401


# --- Logging hygiene ------------------------------------------------------------


def test_cookies_tokens_and_passwords_are_never_logged(
    world: World, password: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    client = csrf_client()
    token = csrf_token(client)
    wrong = f"wrong-{uuid.uuid4().hex}"
    client.post(
        f"{API}/auth/login",
        {"email": world.employee_a1.email, "password": wrong},
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
    _post(client, "/auth/login", {"email": world.employee_a1.email, "password": password})
    response = login(client, world.employee_a1.email, password)
    assert response.status_code == 200
    session_key = _session_key(client)
    rotated_token = str(client.cookies[settings.CSRF_COOKIE_NAME].value)
    client.get(f"{API}/auth/me")
    client.get(f"{API}/branches/{uuid.uuid4()}")
    _post(client, "/auth/logout", **{"X-CSRFToken": rotated_token})

    assert caplog.records, "expected login log lines"
    haystack = caplog.text + "".join(
        repr(record.args) + repr(record.__dict__) for record in caplog.records
    )
    for secret in (password, wrong, token, rotated_token, session_key):
        assert secret not in haystack


@override_settings(DEBUG=True)
def test_debug_mode_does_not_log_sql_passwords_or_session_keys(
    world: World, password: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    assert settings.DEBUG is True
    assert logging.getLogger("django.db.backends").getEffectiveLevel() >= logging.WARNING
    client = csrf_client()

    response = login(client, world.employee_a1.email, password)
    assert response.status_code == 200
    session_key = _session_key(client)
    token = str(client.cookies[settings.CSRF_COOKIE_NAME].value)
    client.get(f"{API}/auth/me")
    _post(client, "/auth/logout", **{"X-CSRFToken": token})

    assert not [r for r in caplog.records if r.name.startswith("django.db.backends")]
    haystack = caplog.text + "".join(repr(r.__dict__) for r in caplog.records)
    assert "SELECT" not in haystack
    assert "pbkdf2" not in haystack and "md5$" not in haystack
    for secret in (password, session_key, token):
        assert secret not in haystack
