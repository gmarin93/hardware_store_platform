import json
import logging
import sys
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from django.db import connection, transaction
from django.test import Client, RequestFactory
from rest_framework.exceptions import ErrorDetail

from common import exceptions as exceptions_module
from common.exceptions import api_exception_handler, flatten_field_errors
from common.log_filters import SensitiveRecordFilter
from common.request_id import RequestIDLogFilter
from common.views import handler500
from organizations.tests.probe_urls import EXPLODE_PATH, PLAIN_PATH
from tests.fixtures import API, World, csrf_client, csrf_token

ENVELOPE_KEYS = {"code", "message", "field_errors", "request_id"}


def _login_post(client: Client, body: Any, **kwargs: Any) -> Any:
    token = csrf_token(client)
    return client.post(f"{API}/auth/login", body, headers={"X-CSRFToken": token}, **kwargs)


@pytest.mark.django_db
def test_validation_error_envelope_with_field_errors() -> None:
    response = _login_post(
        csrf_client(), {"email": "no-es-correo"}, content_type="application/json"
    )

    assert response.status_code == 400
    body = response.json()
    assert set(body) == ENVELOPE_KEYS
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Los datos enviados no son válidos."
    assert set(body["field_errors"]) == {"email", "password"}
    assert body["field_errors"]["password"] == [
        {"code": "required", "message": "Este campo es requerido."}
    ]
    assert body["field_errors"]["email"][0]["code"] == "invalid"
    assert response["X-Request-ID"] == body["request_id"]


@pytest.mark.django_db
def test_parse_error_envelope() -> None:
    response = _login_post(csrf_client(), "{not json", content_type="application/json")

    assert response.status_code == 400
    assert response.json()["code"] == "PARSE_ERROR"
    assert response.json()["field_errors"] == {}


@pytest.mark.django_db
def test_unsupported_media_type_envelope() -> None:
    response = _login_post(csrf_client(), {"email": "a@example.test", "password": "x"})

    assert response.status_code == 415, response.content
    assert response.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.parametrize("method", ["get", "post", "delete"])
def test_unknown_api_path_is_json_404(method: str) -> None:
    response = getattr(csrf_client(), method)(f"{API}/no-existe/en/absoluto")

    assert response.status_code == 404
    body = response.json()
    assert set(body) == ENVELOPE_KEYS
    assert body["code"] == "NOT_FOUND"


def test_non_api_path_is_json_404() -> None:
    response = Client().get("/no-existe")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_method_not_allowed_envelope(world: World) -> None:
    client = Client()
    client.force_login(world.admin_a)

    response = client.delete(f"{API}/auth/me")

    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"


def test_inbound_request_id_is_echoed_when_valid() -> None:
    response = Client().get(f"{API}/auth/me", headers={"X-Request-ID": "web:abc-123.Z_9"})

    assert response["X-Request-ID"] == "web:abc-123.Z_9"
    assert response.json()["request_id"] == "web:abc-123.Z_9"


@pytest.mark.parametrize(
    "inbound", ["has space", "a" * 65, "-leading-dash", "<script>", "ñandú", "x\r\nSet-Cookie: a=b"]
)
def test_invalid_request_id_is_replaced(inbound: str) -> None:
    response = Client().get(f"{API}/auth/me", headers={"X-Request-ID": inbound})

    generated = response["X-Request-ID"]
    assert generated != inbound
    assert str(uuid.UUID(generated)) == generated
    assert response.json()["request_id"] == generated


def test_request_id_generated_when_absent() -> None:
    response = Client().get(f"{API}/health")
    uuid.UUID(response["X-Request-ID"])


def test_flatten_field_errors_nested_and_non_field() -> None:
    detail = {
        "lines": [
            {},
            {"quantity": [ErrorDetail("Inválido.", code="invalid_quantity_increment")]},
        ],
        "non_field_errors": [ErrorDetail("Conflicto.", code="conflict")],
    }
    assert flatten_field_errors(detail) == {
        "lines.1.quantity": [{"code": "invalid_quantity_increment", "message": "Inválido."}],
        "non_field_errors": [{"code": "conflict", "message": "Conflicto."}],
    }
    assert flatten_field_errors([ErrorDetail("Malo.", code="bad")]) == {
        "non_field_errors": [{"code": "bad", "message": "Malo."}]
    }


def test_unexpected_exception_becomes_internal_error(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)
    response = api_exception_handler(RuntimeError("detalle interno secreto"), {})

    assert response.status_code == 500
    assert response.data["code"] == "INTERNAL_ERROR"
    assert "detalle interno secreto" not in str(response.data)


def test_log_filter_uses_request_attached_to_record() -> None:
    record = logging.LogRecord("django.request", logging.WARNING, __file__, 1, "x", (), None)
    record.request = SimpleNamespace(request_id="from-request")
    assert RequestIDLogFilter().filter(record)
    assert getattr(record, "request_id", None) == "from-request"

    bare = logging.LogRecord("app", logging.INFO, __file__, 1, "x", (), None)
    RequestIDLogFilter().filter(bare)
    assert getattr(bare, "request_id", None) == "-"


@pytest.mark.urls("organizations.tests.probe_urls")
def test_unexpected_exception_in_view_is_500_envelope_without_details(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(exceptions_module, "set_rollback", lambda: calls.append(True))
    caplog.set_level(logging.DEBUG)

    response = Client().get(EXPLODE_PATH, headers={"X-Request-ID": "boom-1"})

    assert response.status_code == 500
    assert response.json() == {
        "code": "INTERNAL_ERROR",
        "message": "Ocurrió un error interno. Intente de nuevo más tarde.",
        "field_errors": {},
        "request_id": "boom-1",
    }
    assert calls == [True]  # transaction marked for rollback
    assert "RuntimeError" in caplog.text
    assert "boom-1" in caplog.text
    assert "persona@example.test" not in caplog.text  # message/traceback not logged
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.django_db(transaction=True)
def test_set_rollback_marks_atomic_request_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(connection.settings_dict, "ATOMIC_REQUESTS", True)
    with transaction.atomic():
        api_exception_handler(RuntimeError("x"), {})
        assert transaction.get_rollback() is True


def test_django_handler500_returns_envelope() -> None:
    request = RequestFactory().get("/x", headers={"X-Request-ID": "h500"})
    response = handler500(request)

    assert response.status_code == 500
    assert json.loads(response.content) == {
        "code": "INTERNAL_ERROR",
        "message": "Ocurrió un error interno. Intente de nuevo más tarde.",
        "field_errors": {},
        "request_id": "h500",
    }


@pytest.mark.urls("organizations.tests.probe_urls")
def test_csrf_failure_view_for_plain_django_views(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    client = csrf_client()

    response = client.post(PLAIN_PATH, headers={"Origin": "http://evil.example.test"})

    assert response.status_code == 403
    body = response.json()
    assert set(body) == ENVELOPE_KEYS
    assert body["code"] == "CSRF_FAILED"
    # Django's rejection log would embed the raw Origin/reason; it is redacted.
    csrf_records = [r for r in caplog.records if r.name == "django.security.csrf"]
    assert csrf_records
    assert all(r.getMessage() == f"Forbidden (CSRF): {PLAIN_PATH}" for r in csrf_records)
    assert "evil.example.test" not in caplog.text


def test_django_request_exc_info_is_stripped_when_debug_off() -> None:
    try:
        raise ValueError("persona@example.test")
    except ValueError:
        record = logging.LogRecord(
            "django.request",
            logging.ERROR,
            __file__,
            1,
            "Internal Server Error: %s",
            ("/p",),
            sys.exc_info(),
        )
    assert SensitiveRecordFilter().filter(record)
    assert record.exc_info is None
    assert record.getMessage() == "Internal Server Error: /p [ValueError]"
