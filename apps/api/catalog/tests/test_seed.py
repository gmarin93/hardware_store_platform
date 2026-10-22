"""``seed_synthetic``: local/test guard, idempotency and synthetic labelling.

Reads the real data file ``tests/fixtures/synthetic/p1/catalog.json``. Inside
the API container the repository directory must be mounted at
``/tests/fixtures/synthetic`` (see docs/development/CHECKS.md, P1-02B).
"""

import json
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client

from accounts.models import CustomerProfile, User
from catalog.models import (
    AttributeDefinition,
    AttributeValue,
    Brand,
    CatalogStatus,
    Category,
    Media,
    MediaStatus,
    Product,
    SourceReference,
    Unit,
    Variant,
)
from catalog.seed import default_data_dir
from organizations.models import Branch, BranchMembership, Organization, RoleAssignment
from tests.fixtures import API

pytestmark = pytest.mark.django_db

MODELS: tuple[Any, ...] = (
    Organization,
    Branch,
    Brand,
    Category,
    AttributeDefinition,
    Product,
    Variant,
    AttributeValue,
    Media,
    SourceReference,
    User,
    RoleAssignment,
    BranchMembership,
    CustomerProfile,
)


@pytest.fixture
def data_dir() -> Path:
    path = default_data_dir()
    if not (path / "catalog.json").is_file():
        pytest.fail(
            f"Synthetic data not found at {path}. In Compose, run pytest with "
            '-v "$PWD/tests/fixtures/synthetic:/tests/fixtures/synthetic:ro" (CHECKS.md P1-02B).'
        )
    return path


@pytest.fixture(autouse=True)
def opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_SYNTHETIC_SEED", "1")


class _Terminal(StringIO):
    """Captured stdout that claims to be an interactive terminal."""

    def isatty(self) -> bool:
        return True


def _seed(*args: str, tty: bool = False) -> str:
    out = _Terminal() if tty else StringIO()
    call_command("seed_synthetic", *args, stdout=out)
    return out.getvalue()


def _with_file(data_dir: Path, tmp_path: Path, change: Any) -> str:
    data = json.loads((data_dir / "catalog.json").read_text(encoding="utf-8"))
    change(data)
    (tmp_path / "catalog.json").write_text(json.dumps(data), encoding="utf-8")
    return str(tmp_path)


def _counts() -> dict[str, int]:
    return {model.__name__: model.objects.count() for model in MODELS}


def test_refuses_outside_local_or_test_settings(settings: Any, data_dir: Path) -> None:
    settings.DEBUG = False
    settings.SETTINGS_MODULE = "config.settings.base"
    with pytest.raises(CommandError, match="Rechazado"):
        _seed()
    assert Organization.objects.count() == 0


@pytest.mark.parametrize("value", [None, "", "0", "true", "yes"])
def test_refuses_without_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch, data_dir: Path, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("ALLOW_SYNTHETIC_SEED", raising=False)
    else:
        monkeypatch.setenv("ALLOW_SYNTHETIC_SEED", value)
    with pytest.raises(CommandError, match="ALLOW_SYNTHETIC_SEED=1"):
        _seed()
    assert _counts() == dict.fromkeys(_counts(), 0)


def test_runs_with_debug_on_in_base_settings(settings: Any, data_dir: Path) -> None:
    settings.DEBUG = True
    settings.SETTINGS_MODULE = "config.settings.base"
    _seed()
    assert Organization.objects.filter(slug=settings.DEFAULT_ORGANIZATION_SLUG).exists()


def test_seed_is_idempotent(data_dir: Path) -> None:
    first = _seed()
    counts = _counts()
    second = _seed()
    assert _counts() == counts
    assert "Registros creados: ninguno" in second
    assert "Registros actualizados: ninguno" in first
    assert counts["User"] == 0  # no demo users unless requested


def test_creates_default_and_second_synthetic_organization(data_dir: Path) -> None:
    _seed()
    default = Organization.objects.get(slug=settings.DEFAULT_ORGANIZATION_SLUG)
    assert default.is_synthetic and default.is_active
    assert Organization.objects.count() == 2
    assert all(org.is_synthetic for org in Organization.objects.all())
    assert all("SINTÉTICO" in org.name for org in Organization.objects.all())
    assert Branch.objects.filter(organization=default).count() == 2


def test_default_slug_follows_settings(settings: Any, data_dir: Path) -> None:
    settings.DEFAULT_ORGANIZATION_SLUG = "ferreteria-ficticia-x"
    # Last: every override layer resets SETTINGS_MODULE (Django UserSettingsHolder).
    settings.SETTINGS_MODULE = "config.settings.test"
    _seed()
    assert Organization.objects.filter(slug="ferreteria-ficticia-x", is_synthetic=True).exists()
    assert not Organization.objects.filter(slug="demo").exists()


def test_catalog_content_is_synthetic_and_covers_every_unit(data_dir: Path) -> None:
    _seed()
    default = Organization.objects.get(slug=settings.DEFAULT_ORGANIZATION_SLUG)
    for product in Product.objects.all():
        assert "SINTÉTICO" in product.name
        assert "SINTÉTICO" in product.description
    for variant in Variant.objects.all():
        assert "SINTÉTICO" in variant.name
        assert variant.sales_unit == variant.stock_unit
    for brand in Brand.objects.all():
        assert "SINTÉTICO" in brand.name
    assert all(source.is_synthetic for source in SourceReference.objects.all())
    assert all(".example.test/" in source.source_url for source in SourceReference.objects.all())

    visible = Variant.objects.filter(
        organization=default,
        status=CatalogStatus.PUBLISHED,
        product__status=CatalogStatus.PUBLISHED,
    )
    assert set(visible.values_list("sales_unit", flat=True)) == set(Unit.values)
    assert visible.filter(quantity_increment="0.001").exists()

    for org in Organization.objects.all():
        assert Product.objects.filter(organization=org, status=CatalogStatus.DRAFT).exists()
    assert Product.objects.filter(organization=default, status=CatalogStatus.ARCHIVED).exists()
    assert Variant.objects.filter(organization=default, status=CatalogStatus.DRAFT).exists()
    assert Media.objects.filter(organization=default, status=MediaStatus.DRAFT).exists()
    assert AttributeValue.objects.filter(organization=default, is_published=False).exists()
    # Both organizations use one SKU, so cross-organization lookups are testable.
    assert Variant.objects.filter(sku="SIN-TOR-8X1").count() == 2


def test_seeded_public_catalog(data_dir: Path) -> None:
    _seed()
    client = Client()
    rows = client.get(f"{API}/catalog/products", {"page_size": 100}).json()["results"]
    assert len(rows) == 7
    assert all("SINTÉTICO" in row["name"] for row in rows)
    body = client.get(f"{API}/catalog/variants", {"sku": "sin-tor-8x1"}).json()
    default = Organization.objects.get(slug=settings.DEFAULT_ORGANIZATION_SLUG)
    assert [row["id"] for row in body["results"]] == [
        str(Variant.objects.get(organization=default, sku="SIN-TOR-8X1").id)
    ]


def test_demo_users_only_with_flag_and_passwords_printed_once_on_a_terminal(
    data_dir: Path,
) -> None:
    _seed()
    assert User.objects.count() == 0

    output = _seed("--with-demo-users", tty=True)
    users = list(User.objects.all())
    assert len(users) == 5
    assert all(user.email.endswith("@example.test") for user in users)
    printed = {
        parts[0]: parts[1]
        for line in output.splitlines()
        if (parts := line.split()) and len(parts) == 2 and parts[0].endswith("@example.test")
    }
    assert set(printed) == {user.email for user in users}
    assert len(set(printed.values())) == 5
    for email, password in printed.items():
        assert len(password) >= 20
        assert authenticate(email=email, password=password) is not None

    default = Organization.objects.get(slug=settings.DEFAULT_ORGANIZATION_SLUG)
    assert RoleAssignment.objects.filter(
        organization=default, user__email="admin.demo@example.test"
    )
    assert BranchMembership.objects.filter(
        user__email="empleado.central@example.test", branch__code="central"
    ).exists()
    assert CustomerProfile.objects.filter(
        user__email="cliente.demo@example.test", organization=default
    ).exists()

    again = _seed("--with-demo-users", tty=True)
    assert User.objects.count() == 5
    for password in printed.values():
        assert password not in again
    assert "ya existía; contraseña sin cambios" in again
    for email, password in printed.items():
        assert authenticate(email=email, password=password) is not None


def test_non_terminal_output_never_contains_passwords(data_dir: Path) -> None:
    output = _seed("--with-demo-users")
    users = list(User.objects.all())
    assert len(users) == 5
    assert all(not user.has_usable_password() for user in users)
    assert "SIN contraseña utilizable" in output
    for user in users:
        assert f"manage.py changepassword {user.email}" in output
    lines = [line.split() for line in output.splitlines()]
    assert not [p for p in lines if len(p) == 2 and p[0].endswith("@example.test")]


def test_existing_demo_accounts_are_reused_and_roles_reactivated(data_dir: Path) -> None:
    _seed("--with-demo-users")
    RoleAssignment.objects.update(is_active=False)
    BranchMembership.objects.update(is_active=False)
    before = {u.email: u.password for u in User.objects.all()}
    _seed("--with-demo-users", tty=True)
    assert {u.email: u.password for u in User.objects.all()} == before
    assert not RoleAssignment.objects.filter(is_active=False).exists()
    assert not BranchMembership.objects.filter(is_active=False).exists()


@pytest.mark.parametrize("slug", ["ferreteria-real", "demo"])
def test_refuses_when_any_non_synthetic_organization_exists(data_dir: Path, slug: str) -> None:
    Organization.objects.create(slug=slug, name="Organización no sintética", is_synthetic=False)
    with pytest.raises(CommandError, match="no sintética"):
        _seed("--with-demo-users")
    assert Organization.objects.count() == 1
    assert Product.objects.count() == 0
    assert User.objects.count() == 0


def test_moving_a_sku_to_another_product_fails_cleanly(data_dir: Path, tmp_path: Path) -> None:
    _seed()
    counts = _counts()
    snapshot = sorted(Variant.objects.values_list("sku", "product_id"))

    def move(data: Any) -> None:
        products = data["organizations"][0]["products"]
        products[1]["variants"].append(products[0]["variants"].pop(0))  # SIN-TOR-8X1

    with pytest.raises(CommandError, match="ya pertenece a otro producto"):
        _seed("--data-dir", _with_file(data_dir, tmp_path, move))
    assert _counts() == counts
    assert sorted(Variant.objects.values_list("sku", "product_id")) == snapshot


def test_unexpected_constraint_violation_is_a_clean_seed_error(
    data_dir: Path, tmp_path: Path
) -> None:
    def duplicate_media(data: Any) -> None:
        media = data["organizations"][0]["products"][0]["media"]
        media.append({**media[0], "url": media[0]["url"] + " x"})  # whitespace: DB check

    with pytest.raises(CommandError, match="no se guardó nada"):
        _seed("--data-dir", _with_file(data_dir, tmp_path, duplicate_media))
    assert _counts() == dict.fromkeys(_counts(), 0)


def test_refuses_to_take_over_a_non_synthetic_organization(data_dir: Path) -> None:
    Organization.objects.create(
        slug=settings.DEFAULT_ORGANIZATION_SLUG,
        name="Organización no sintética",
        is_synthetic=False,
    )
    with pytest.raises(CommandError, match="no sintética"):
        _seed()
    assert Product.objects.count() == 0
    assert Organization.objects.get().name == "Organización no sintética"


def test_unlabelled_data_is_rejected_atomically(data_dir: Path, tmp_path: Path) -> None:
    data = json.loads((data_dir / "catalog.json").read_text(encoding="utf-8"))
    data["organizations"][0]["products"][-1]["name"] = "Producto sin etiqueta"
    (tmp_path / "catalog.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CommandError, match="SINTÉTICO"):
        _seed("--data-dir", str(tmp_path))
    assert Organization.objects.count() == 0
    assert Product.objects.count() == 0


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("source", "url_prefix"), "https://tienda-real.com/", "example.test"),
        (("source", "url_prefix"), "https://evil.com/.example.test/", "example.test"),
        (("source", "url_prefix"), "https://example.test.evil.com/", "example.test"),
        (("source", "url_prefix"), "http://datos.example.test/", "example.test"),
        (("source", "url_prefix"), "https://user@datos.example.test/", "example.test"),
        (("organizations", 0, "demo_users", 0, "email"), "persona@gmail.com", "example.test"),
        (("organizations", 0, "products", 0, "media", 0, "url"), "https://x.test/a.png", "local"),
        (("format",), "otro", "formato"),
    ],
)
def test_data_file_is_validated_as_data(
    data_dir: Path, tmp_path: Path, path: tuple[Any, ...], value: str, message: str
) -> None:
    data = json.loads((data_dir / "catalog.json").read_text(encoding="utf-8"))
    target: Any = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    (tmp_path / "catalog.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CommandError, match=message):
        _seed("--data-dir", str(tmp_path), "--with-demo-users")
    assert Organization.objects.count() == 0
    assert User.objects.count() == 0
