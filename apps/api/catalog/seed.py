"""Idempotent loader for the synthetic P1 catalog (``tests/fixtures/synthetic/p1``).

The data file is treated as data, never as instructions: every value is
type-checked and the loader refuses records that are not visibly synthetic
(``SINTÉTICO`` in every organization, branch, brand, category, product and
variant name and in product descriptions; ``example.test`` emails).

Natural keys make re-runs create nothing new: organization ``slug``; branch,
brand and category ``(organization, code/slug)``; attribute definition
``(organization, code)``; product = its synthetic ``SourceReference``
``(organization, source name, external_id)``; variant ``(organization, sku)``;
attribute value ``(definition, product|variant)``; media ``(product, variant, url)``.
Existing rows are updated to the file's values.

Guard (all required): ``DEBUG`` on or the ``config.settings.test`` settings
module; the explicit opt-in ``ALLOW_SYNTHETIC_SEED=1`` in the environment; and
no non-synthetic ``Organization`` in the database at all.

Demo users are created only on request. With ``reveal_passwords`` (the command
sets it only when stdout is a TTY) passwords are generated with ``secrets`` and
returned to the caller, which prints them once; otherwise the users get an
unusable password and must be given one with ``manage.py changepassword``.
Passwords are never written to files. Existing ``@example.test`` accounts are
reused: their password is left unchanged and their synthetic role rows are
(re)activated.
"""

import json
import os
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction

from accounts.models import CustomerProfile, User
from catalog.models import (
    AttributeDefinition,
    AttributeValue,
    AttributeValueType,
    Brand,
    CatalogStatus,
    Category,
    Media,
    MediaStatus,
    Product,
    SourceReference,
    Unit,
    Variant,
    normalize_sku,
)
from organizations.models import Branch, BranchMembership, Organization, RoleAssignment

DATA_FORMAT = "hardware-store-synthetic-catalog"
DATA_VERSION = 1
SYNTHETIC_LABEL = "SINTÉTICO"
DEMO_EMAIL_DOMAIN = "@example.test"
TEST_SETTINGS_MODULE = "config.settings.test"
OPT_IN_ENV = "ALLOW_SYNTHETIC_SEED"
SOURCE_HOST = "example.test"
DEMO_ROLES = frozenset({"ADMIN", "EMPLOYEE", "CUSTOMER"})


class SeedError(Exception):
    """Invalid data file or unsafe environment; nothing is written."""


def default_data_dir() -> Path:
    """``<repo>/tests/fixtures/synthetic/p1`` relative to ``apps/api``.

    In the API container (``BASE_DIR = /app``) this is
    ``/tests/fixtures/synthetic/p1``; mount the repository directory there.
    """
    return Path(settings.BASE_DIR).parent.parent / "tests" / "fixtures" / "synthetic" / "p1"


def seed_allowed() -> bool:
    """Environment guard: (``DEBUG`` on or test settings) and ``ALLOW_SYNTHETIC_SEED=1``."""
    local = settings.DEBUG is True or getattr(settings, "SETTINGS_MODULE", None) == (
        TEST_SETTINGS_MODULE
    )
    return local and os.environ.get(OPT_IN_ENV) == "1"


REFUSED_MESSAGE = (
    "Rechazado: seed_synthetic solo se ejecuta en un entorno local o de prueba "
    f"(DEBUG activo o {TEST_SETTINGS_MODULE}) y con {OPT_IN_ENV}=1."
)


@dataclass
class SeedResult:
    created: dict[str, int] = field(default_factory=dict)
    updated: dict[str, int] = field(default_factory=dict)
    # (email, generated password or None if unusable) for users created in this run only.
    new_users: list[tuple[str, str | None]] = field(default_factory=list)
    existing_users: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)

    def count(self, kind: str, created: bool) -> None:
        target = self.created if created else self.updated
        target[kind] = target.get(kind, 0) + 1


# --- Data validation helpers --------------------------------------------------------


def _obj(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SeedError(f"{where}: se esperaba un objeto.")
    return value


def _list(value: Any, where: str) -> Sequence[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SeedError(f"{where}: se esperaba una lista.")
    return value


def _str(data: Mapping[str, Any], key: str, where: str, *, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str) or (default is None and not value.strip()):
        raise SeedError(f"{where}.{key}: se esperaba texto.")
    return value


def _labelled(data: Mapping[str, Any], key: str, where: str) -> str:
    value = _str(data, key, where)
    if SYNTHETIC_LABEL not in value:
        raise SeedError(f"{where}.{key}: debe contener «{SYNTHETIC_LABEL}».")
    return value


def _choice(data: Mapping[str, Any], key: str, where: str, allowed: Sequence[str]) -> str:
    value = _str(data, key, where)
    if value not in allowed:
        raise SeedError(f"{where}.{key}: valor no permitido.")
    return value


def _decimal(value: Any, where: str) -> Decimal:
    if not isinstance(value, str):
        raise SeedError(f"{where}: se esperaba un decimal como texto.")
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise SeedError(f"{where}: decimal no válido.") from exc


def load_data(data_dir: Path) -> Mapping[str, Any]:
    path = data_dir / "catalog.json"
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SeedError(f"No se pudo leer {path}.") from exc
    try:
        data = _obj(json.loads(raw), "catalog.json")
    except json.JSONDecodeError as exc:
        raise SeedError(f"{path} no es JSON válido.") from exc
    if data.get("format") != DATA_FORMAT or data.get("version") != DATA_VERSION:
        raise SeedError(f"{path}: formato o versión no reconocidos.")
    return data


# --- Loader -------------------------------------------------------------------------


@dataclass
class _Context:
    result: SeedResult
    source_name: str
    source_url_prefix: str
    observed_at: datetime
    reveal_passwords: bool = False


def seed(
    data: Mapping[str, Any], *, with_demo_users: bool = False, reveal_passwords: bool = False
) -> SeedResult:
    """Validate and load ``data`` in one transaction. Raises ``SeedError``."""
    if not seed_allowed():
        raise SeedError(REFUSED_MESSAGE)
    source = _obj(data.get("source"), "source")
    try:
        observed_at = datetime.fromisoformat(_str(source, "observed_at", "source"))
    except ValueError as exc:
        raise SeedError("source.observed_at: fecha ISO 8601 no válida.") from exc
    if observed_at.tzinfo is None:
        raise SeedError("source.observed_at: debe incluir zona horaria.")
    url_prefix = _str(source, "url_prefix", "source")
    parts = urlsplit(url_prefix)
    host = (parts.hostname or "").lower()
    if (
        parts.scheme != "https"
        or not (host == SOURCE_HOST or host.endswith(f".{SOURCE_HOST}"))
        or parts.username is not None
        or parts.password is not None
        or parts.port is not None
        or not url_prefix.endswith("/")
        or any(c.isspace() or c == "\\" for c in url_prefix)
    ):
        raise SeedError("source.url_prefix: debe ser https://<dominio ficticio>.example.test/….")
    ctx = _Context(
        result=SeedResult(),
        source_name=_str(source, "name", "source"),
        source_url_prefix=url_prefix,
        observed_at=observed_at,
    )
    organizations = _list(data.get("organizations"), "organizations")
    if not organizations:
        raise SeedError("organizations: se requiere al menos una organización.")
    slugs = [
        _obj(o, f"organizations[{i}]").get("slug") or settings.DEFAULT_ORGANIZATION_SLUG
        for i, o in enumerate(organizations)
    ]
    if settings.DEFAULT_ORGANIZATION_SLUG not in slugs or len(set(slugs)) != len(slugs):
        raise SeedError("organizations: debe incluir la organización por defecto una sola vez.")
    ctx.reveal_passwords = reveal_passwords
    try:
        with transaction.atomic():
            # Serialize concurrent seeds and refuse to run next to real data.
            list(Organization.objects.select_for_update().values_list("id", flat=True))
            if Organization.objects.filter(is_synthetic=False).exists():
                raise SeedError(
                    "Existe al menos una organización no sintética; seed_synthetic no se ejecuta."
                )
            for index, (org_data, slug) in enumerate(zip(organizations, slugs, strict=True)):
                _seed_organization(
                    ctx, _obj(org_data, f"organizations[{index}]"), slug, with_demo_users
                )
    except IntegrityError as exc:
        # Any constraint the validation above did not anticipate: full rollback.
        raise SeedError(
            "Los datos sintéticos contradicen restricciones de la base de datos; no se guardó nada."
        ) from exc
    return ctx.result


def _seed_organization(
    ctx: _Context, data: Mapping[str, Any], slug: str, with_demo_users: bool
) -> None:
    where = f"organizations[{slug}]"
    name = _labelled(data, "name", where)
    org, created = Organization.objects.update_or_create(
        slug=slug, defaults={"name": name, "is_synthetic": True, "is_active": True}
    )
    ctx.result.count("organization", created)
    ctx.result.organizations.append(slug)

    branches: dict[str, Branch] = {}
    for i, raw in enumerate(_list(data.get("branches"), f"{where}.branches")):
        item = _obj(raw, f"{where}.branches[{i}]")
        code = _str(item, "code", f"{where}.branches[{i}]")
        branch, created = Branch.objects.update_or_create(
            organization=org,
            code=code,
            defaults={"name": _labelled(item, "name", f"{where}.branches[{i}]"), "is_active": True},
        )
        branches[code] = branch
        ctx.result.count("branch", created)

    brands: dict[str, Brand] = {}
    for i, raw in enumerate(_list(data.get("brands"), f"{where}.brands")):
        item = _obj(raw, f"{where}.brands[{i}]")
        slug_value = _str(item, "slug", f"{where}.brands[{i}]")
        brand, created = Brand.objects.update_or_create(
            organization=org,
            slug=slug_value,
            defaults={"name": _labelled(item, "name", f"{where}.brands[{i}]")},
        )
        brands[slug_value] = brand
        ctx.result.count("brand", created)

    categories: dict[str, Category] = {}
    for i, raw in enumerate(_list(data.get("categories"), f"{where}.categories")):
        item_where = f"{where}.categories[{i}]"
        item = _obj(raw, item_where)
        slug_value = _str(item, "slug", item_where)
        parent_slug = item.get("parent")
        if parent_slug is not None and parent_slug not in categories:
            raise SeedError(f"{item_where}.parent: debe declararse antes.")
        category, created = Category.objects.update_or_create(
            organization=org,
            slug=slug_value,
            defaults={
                "name": _labelled(item, "name", item_where),
                "parent": categories[parent_slug] if parent_slug is not None else None,
            },
        )
        categories[slug_value] = category
        ctx.result.count("category", created)

    definitions: dict[str, AttributeDefinition] = {}
    for i, raw in enumerate(_list(data.get("attribute_definitions"), f"{where}.attributes")):
        item_where = f"{where}.attribute_definitions[{i}]"
        item = _obj(raw, item_where)
        code = _str(item, "code", item_where)
        definition, created = AttributeDefinition.objects.update_or_create(
            organization=org,
            code=code,
            defaults={
                "name": _str(item, "name", item_where),
                "value_type": _choice(item, "value_type", item_where, AttributeValueType.values),
                "unit": _str(item, "unit", item_where, default=""),
            },
        )
        definitions[code] = definition
        ctx.result.count("attribute_definition", created)

    for i, raw in enumerate(_list(data.get("products"), f"{where}.products")):
        _seed_product(
            ctx, org, _obj(raw, f"{where}.products[{i}]"), brands, categories, definitions
        )

    if with_demo_users:
        for i, raw in enumerate(_list(data.get("demo_users"), f"{where}.demo_users")):
            _seed_user(ctx, org, _obj(raw, f"{where}.demo_users[{i}]"), branches)


def _source_defaults(ctx: _Context, external_id: str) -> dict[str, Any]:
    return {
        "source_url": f"{ctx.source_url_prefix}{external_id}",
        "observed_at": ctx.observed_at,
        "is_synthetic": True,
    }


def _seed_product(
    ctx: _Context,
    org: Organization,
    data: Mapping[str, Any],
    brands: Mapping[str, Brand],
    categories: Mapping[str, Category],
    definitions: Mapping[str, AttributeDefinition],
) -> None:
    external_id = _str(data, "external_id", "product")
    where = f"product[{external_id}]"
    brand_slug, category_slug = data.get("brand"), data.get("category")
    if brand_slug is not None and brand_slug not in brands:
        raise SeedError(f"{where}.brand: marca desconocida.")
    if category_slug is not None and category_slug not in categories:
        raise SeedError(f"{where}.category: categoría desconocida.")
    fields = {
        "name": _labelled(data, "name", where),
        "description": _labelled(data, "description", where),
        "status": _choice(data, "status", where, CatalogStatus.values),
        "brand": brands[brand_slug] if brand_slug is not None else None,
        "category": categories[category_slug] if category_slug is not None else None,
        "internal_notes": _str(data, "internal_notes", where, default=""),
    }
    source = (
        SourceReference.objects.select_related("product")
        .filter(organization=org, source_name=ctx.source_name, external_id=external_id)
        .first()
    )
    if source is not None and source.product is not None:
        product = source.product
        for key, value in fields.items():
            setattr(product, key, value)
        product.save()
        ctx.result.count("product", False)
    else:
        product = Product.objects.create(organization=org, **fields)
        ctx.result.count("product", True)
    _, created = SourceReference.objects.update_or_create(
        organization=org,
        source_name=ctx.source_name,
        external_id=external_id,
        defaults={**_source_defaults(ctx, external_id), "product": product, "variant": None},
    )
    ctx.result.count("source_reference", created)

    _seed_attributes(ctx, org, data, where, definitions, product=product)
    _seed_media(ctx, org, data, where, product, None)
    for i, raw in enumerate(_list(data.get("variants"), f"{where}.variants")):
        _seed_variant(ctx, org, product, _obj(raw, f"{where}.variants[{i}]"), definitions)


def _seed_variant(
    ctx: _Context,
    org: Organization,
    product: Product,
    data: Mapping[str, Any],
    definitions: Mapping[str, AttributeDefinition],
) -> None:
    sku = normalize_sku(_str(data, "sku", "variant"))
    where = f"variant[{sku}]"
    unit = _choice(data, "unit", where, Unit.values)
    current_product = (
        Variant.objects.filter(organization=org, sku=sku)
        .values_list("product_id", flat=True)
        .first()
    )
    if current_product is not None and current_product != product.id:
        raise SeedError(f"{where}: el SKU ya pertenece a otro producto; no se mueve.")
    variant, created = Variant.objects.update_or_create(
        organization=org,
        sku=sku,
        defaults={
            "product": product,
            "name": _labelled(data, "name", where),
            "status": _choice(data, "status", where, CatalogStatus.values),
            "sales_unit": unit,
            "stock_unit": unit,
            "quantity_increment": _decimal(data.get("increment"), f"{where}.increment"),
            "min_quantity": _decimal(data.get("min_quantity"), f"{where}.min_quantity"),
            "supplier_code": _str(data, "supplier_code", where, default=""),
            "internal_notes": _str(data, "internal_notes", where, default=""),
        },
    )
    ctx.result.count("variant", created)
    external_id = f"VAR-{sku}"
    _, created = SourceReference.objects.update_or_create(
        organization=org,
        source_name=ctx.source_name,
        external_id=external_id,
        defaults={**_source_defaults(ctx, external_id), "product": None, "variant": variant},
    )
    ctx.result.count("source_reference", created)
    _seed_attributes(ctx, org, data, where, definitions, variant=variant)
    _seed_media(ctx, org, data, where, product, variant)


def _typed_value(definition: AttributeDefinition, value: Any, where: str) -> dict[str, Any]:
    values: dict[str, Any] = {"value_decimal": None, "value_text": None, "value_boolean": None}
    if definition.value_type == AttributeValueType.DECIMAL:
        values["value_decimal"] = _decimal(value, where)
    elif definition.value_type == AttributeValueType.BOOLEAN:
        if not isinstance(value, bool):
            raise SeedError(f"{where}: se esperaba true o false.")
        values["value_boolean"] = value
    else:
        if not isinstance(value, str) or not value:
            raise SeedError(f"{where}: se esperaba texto.")
        values["value_text"] = value
    return values


def _seed_attributes(
    ctx: _Context,
    org: Organization,
    data: Mapping[str, Any],
    where: str,
    definitions: Mapping[str, AttributeDefinition],
    *,
    product: Product | None = None,
    variant: Variant | None = None,
) -> None:
    for i, raw in enumerate(_list(data.get("attributes"), f"{where}.attributes")):
        item_where = f"{where}.attributes[{i}]"
        item = _obj(raw, item_where)
        code = _str(item, "code", item_where)
        definition = definitions.get(code)
        if definition is None:
            raise SeedError(f"{item_where}.code: atributo desconocido.")
        unit = _str(item, "unit", item_where, default=definition.unit)
        if unit != definition.unit:
            raise SeedError(f"{item_where}.unit: debe ser «{definition.unit}».")
        published = item.get("published", False)
        if not isinstance(published, bool):
            raise SeedError(f"{item_where}.published: se esperaba true o false.")
        _, created = AttributeValue.objects.update_or_create(
            organization=org,
            definition=definition,
            product=product,
            variant=variant,
            defaults={
                **_typed_value(definition, item.get("value"), f"{item_where}.value"),
                "value_type": definition.value_type,
                "unit": unit,
                "is_published": published,
            },
        )
        ctx.result.count("attribute_value", created)


def _seed_media(
    ctx: _Context,
    org: Organization,
    data: Mapping[str, Any],
    where: str,
    product: Product,
    variant: Variant | None,
) -> None:
    for i, raw in enumerate(_list(data.get("media"), f"{where}.media")):
        item_where = f"{where}.media[{i}]"
        item = _obj(raw, item_where)
        url = _str(item, "url", item_where)
        if not url.startswith("/catalog-media/sintetico/"):
            raise SeedError(f"{item_where}.url: solo rutas locales /catalog-media/sintetico/.")
        sort_order = item.get("sort_order", 0)
        if not isinstance(sort_order, int) or isinstance(sort_order, bool) or sort_order < 0:
            raise SeedError(f"{item_where}.sort_order: entero no negativo.")
        _, created = Media.objects.update_or_create(
            organization=org,
            product=product,
            variant=variant,
            url=url,
            defaults={
                "alt_text": _labelled(item, "alt_text", item_where),
                "status": _choice(item, "status", item_where, MediaStatus.values),
                "sort_order": sort_order,
            },
        )
        ctx.result.count("media", created)


def _seed_user(
    ctx: _Context, org: Organization, data: Mapping[str, Any], branches: Mapping[str, Branch]
) -> None:
    email = _str(data, "email", "demo_user").strip().lower()
    where = f"demo_user[{email}]"
    if not email.endswith(DEMO_EMAIL_DOMAIN):
        raise SeedError(f"{where}: solo correos {DEMO_EMAIL_DOMAIN}.")
    role = _choice(data, "role", where, sorted(DEMO_ROLES))
    member_of = _list(data.get("branches"), f"{where}.branches")
    if role == "EMPLOYEE" and not member_of:
        raise SeedError(f"{where}.branches: un empleado necesita al menos una sucursal.")
    if any(not isinstance(code, str) or code not in branches for code in member_of):
        raise SeedError(f"{where}.branches: sucursal desconocida.")

    user = User.objects.filter(email=email).first()
    if user is None:
        # create_user(password=None) stores an unusable password.
        user = User.objects.create_user(email, None, full_name=_labelled(data, "full_name", where))
        password: str | None = None
        if ctx.reveal_passwords:
            password = secrets.token_urlsafe(18)
            validate_password(password, user)
            user.set_password(password)
            user.save(update_fields=["password"])
        ctx.result.new_users.append((email, password))
        ctx.result.count("user", True)
    else:
        ctx.result.existing_users.append(email)
        ctx.result.count("user", False)

    if role == "ADMIN":
        RoleAssignment.objects.update_or_create(
            user=user,
            organization=org,
            role=RoleAssignment.RoleName.ADMIN,
            defaults={"is_active": True},
        )
    elif role == "EMPLOYEE":
        for code in member_of:
            BranchMembership.objects.update_or_create(
                user=user, branch=branches[code], defaults={"is_active": True}
            )
    else:
        CustomerProfile.objects.update_or_create(user=user, defaults={"organization": org})
