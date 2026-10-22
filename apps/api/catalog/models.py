"""Catalog: brands, categories, products (families), variants (SKUs), typed
attributes, approved media and staff-only source provenance (ADR 0001 "Catalog
and units (P1 scope)").

Every business row carries ``organization``. Cross-row organization integrity is
enforced twice: ``save()`` raises ``ValidationError`` (service layer) and the
migration adds composite foreign keys ``(fk_id, organization_id) -> (id,
organization_id)`` so a bulk update or raw SQL cannot link rows of different
organizations either (database layer).

There are deliberately no price, cost, stock or availability fields (D07/D09).
"""

import uuid
from decimal import Decimal
from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Mod
from django.db.models.lookups import Exact

from organizations.models import Organization

QUANTITY_MAX_DIGITS = 14
QUANTITY_DECIMAL_PLACES = 3
SKU_MAX_LENGTH = 64
# Canonical SKU: uppercase ASCII letters/digits, then also ".", "_" or "-".
SKU_PATTERN = r"^[A-Z0-9][A-Z0-9._-]{0,63}$"
# Approved catalog images are referenced, never fetched: a site-relative path
# (not protocol-relative "//host" or "/\\host") or an https URL, no whitespace.
MEDIA_URL_PATTERN = r"^(/[^/\\\s]\S*|https://\S+)$"
# Staff-only provenance links: empty or an https URL without whitespace.
SOURCE_URL_PATTERN = r"^https://\S+$"


class CatalogStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    PUBLISHED = "PUBLISHED", "Publicado"
    ARCHIVED = "ARCHIVED", "Archivado"


class Unit(models.TextChoices):
    """Sales/stock units (P1 enum). Product dimensions use ``AttributeUnit``."""

    PIECE = "piece", "pieza"
    M = "m", "metro"
    CM = "cm", "centímetro"
    KG = "kg", "kilogramo"
    G = "g", "gramo"
    L = "l", "litro"


class AttributeValueType(models.TextChoices):
    DECIMAL = "DECIMAL", "Decimal"
    TEXT = "TEXT", "Texto"
    BOOLEAN = "BOOLEAN", "Sí/No"


class AttributeUnit(models.TextChoices):
    """Units of typed product attributes (dimensions, ratings); "" = none."""

    NONE = "", "sin unidad"
    MM = "mm", "milímetro"
    CM = "cm", "centímetro"
    M = "m", "metro"
    IN = "in", "pulgada"
    G = "g", "gramo"
    KG = "kg", "kilogramo"
    ML = "ml", "mililitro"
    L = "l", "litro"
    V = "V", "voltio"
    A = "A", "amperio"
    W = "W", "vatio"


class MediaStatus(models.TextChoices):
    APPROVED = "APPROVED", "Aprobada"
    DRAFT = "DRAFT", "Borrador"


def _choices_check(
    field: str, choices: type[models.TextChoices], name: str
) -> models.CheckConstraint:
    return models.CheckConstraint(condition=Q(**{f"{field}__in": choices.values}), name=name)


def _id_org_unique(prefix: str) -> models.UniqueConstraint:
    # Target of the composite same-organization foreign keys (see migration 0002).
    return models.UniqueConstraint(fields=["id", "organization"], name=f"{prefix}_id_org_uniq")


class OrganizationScopedModel(models.Model):
    """UUID pk, organization and timestamps; same-organization checks on save."""

    # Foreign keys whose target must belong to ``self.organization``.
    same_organization_fields: ClassVar[tuple[str, ...]] = ()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.check_same_organization()
        super().save(*args, **kwargs)

    def check_same_organization(self) -> None:
        for name in self.same_organization_fields:
            related = getattr(self, name)
            if related is not None and related.organization_id != self.organization_id:
                raise ValidationError(
                    {name: "Debe pertenecer a la misma organización."}, code="cross_organization"
                )


class Brand(OrganizationScopedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["organization", "slug"], name="catalog_brand_unique_slug"
            ),
            _id_org_unique("catalog_brand"),
        ]

    def __str__(self) -> str:
        return self.slug


class Category(OrganizationScopedModel):
    same_organization_fields = ("parent",)

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["organization", "slug"], name="catalog_category_unique_slug"
            ),
            models.CheckConstraint(
                condition=~Q(parent=F("id")), name="catalog_category_not_own_parent"
            ),
            _id_org_unique("catalog_category"),
        ]

    def __str__(self) -> str:
        return self.slug


class Product(OrganizationScopedModel):
    """A product family. Public visibility requires ``status == PUBLISHED``."""

    same_organization_fields = ("brand", "category")

    status = models.CharField(
        max_length=16, choices=CatalogStatus.choices, default=CatalogStatus.DRAFT
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    brand = models.ForeignKey(
        Brand, null=True, blank=True, on_delete=models.PROTECT, related_name="products"
    )
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.PROTECT, related_name="products"
    )
    # Staff-only.
    internal_notes = models.TextField(blank=True, default="")

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            _choices_check("status", CatalogStatus, "catalog_product_status_known"),
            _id_org_unique("catalog_product"),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["organization", "status", "name", "id"], name="catalog_prod_org_st_name"
            ),
        ]

    def __str__(self) -> str:
        return str(self.id)


class Variant(OrganizationScopedModel):
    """A sellable SKU. Quantities are NUMERIC(14,3); P1 requires sales_unit == stock_unit.

    Public visibility requires the variant *and* its product to be PUBLISHED.
    """

    same_organization_fields = ("product",)

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="variants")
    sku = models.CharField(max_length=SKU_MAX_LENGTH)
    status = models.CharField(
        max_length=16, choices=CatalogStatus.choices, default=CatalogStatus.DRAFT
    )
    name = models.CharField(max_length=200)
    sales_unit = models.CharField(max_length=8, choices=Unit.choices)
    stock_unit = models.CharField(max_length=8, choices=Unit.choices)
    quantity_increment = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES
    )
    min_quantity = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES
    )
    # Staff-only.
    supplier_code = models.CharField(max_length=64, blank=True, default="")
    internal_notes = models.TextField(blank=True, default="")

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["organization", "sku"], name="catalog_variant_unique_sku"
            ),
            models.CheckConstraint(
                condition=Q(sku__regex=SKU_PATTERN), name="catalog_variant_sku_format"
            ),
            _choices_check("status", CatalogStatus, "catalog_variant_status_known"),
            _choices_check("sales_unit", Unit, "catalog_variant_sales_unit_known"),
            _choices_check("stock_unit", Unit, "catalog_variant_stock_unit_known"),
            # P1: no unit conversion (deferred to a P3 ADR).
            models.CheckConstraint(
                condition=Q(sales_unit=F("stock_unit")), name="catalog_variant_sales_eq_stock_unit"
            ),
            models.CheckConstraint(
                condition=Q(quantity_increment__gt=Decimal(0)),
                name="catalog_variant_increment_positive",
            ),
            models.CheckConstraint(
                condition=Q(min_quantity__gt=Decimal(0)), name="catalog_variant_min_qty_positive"
            ),
            models.CheckConstraint(
                condition=Exact(Mod(F("min_quantity"), F("quantity_increment")), Decimal(0)),
                name="catalog_variant_min_qty_multiple",
            ),
            _id_org_unique("catalog_variant"),
            # Target of Media's (variant_id, product_id) composite foreign key.
            models.UniqueConstraint(
                fields=["id", "product"], name="catalog_variant_id_product_uniq"
            ),
        ]

    def __str__(self) -> str:
        return self.sku

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.sku = normalize_sku(self.sku)
        super().save(*args, **kwargs)


def normalize_sku(raw: str) -> str:
    """Canonical SKU form: surrounding whitespace removed, ASCII uppercase."""
    return raw.strip().upper()


class AttributeDefinition(OrganizationScopedModel):
    """A typed attribute (e.g. diámetro nominal in ``in``). ``unit`` only for DECIMAL."""

    code = models.SlugField(max_length=64)
    name = models.CharField(max_length=120)
    value_type = models.CharField(max_length=8, choices=AttributeValueType.choices)
    unit = models.CharField(max_length=8, choices=AttributeUnit.choices, blank=True, default="")

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="catalog_attrdef_unique_code"
            ),
            _choices_check("value_type", AttributeValueType, "catalog_attrdef_type_known"),
            _choices_check("unit", AttributeUnit, "catalog_attrdef_unit_known"),
            models.CheckConstraint(
                condition=Q(value_type=AttributeValueType.DECIMAL) | Q(unit=""),
                name="catalog_attrdef_unit_only_decimal",
            ),
            _id_org_unique("catalog_attrdef"),
            # Target of AttributeValue's (definition_id, value_type, unit) foreign key.
            models.UniqueConstraint(
                fields=["id", "value_type", "unit"], name="catalog_attrdef_id_type_unit_uniq"
            ),
        ]

    def __str__(self) -> str:
        return self.code


_ONE_TARGET = Q(product__isnull=False, variant__isnull=True) | Q(
    product__isnull=True, variant__isnull=False
)


class AttributeValue(OrganizationScopedModel):
    """Value of a definition for exactly one product or one variant.

    ``value_type`` and ``unit`` repeat the definition's; a composite foreign key
    ``(definition_id, value_type, unit)`` keeps them equal, and a check ensures
    exactly the matching value column is set. Only ``is_published`` values are
    public.
    """

    same_organization_fields = ("definition", "product", "variant")

    definition = models.ForeignKey(AttributeDefinition, on_delete=models.PROTECT, related_name="+")
    product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.CASCADE, related_name="attribute_values"
    )
    variant = models.ForeignKey(
        Variant, null=True, blank=True, on_delete=models.CASCADE, related_name="attribute_values"
    )
    value_type = models.CharField(max_length=8, choices=AttributeValueType.choices)
    value_decimal = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    # NULL (not "") means "not this type"; required by the typed-value check.
    value_text = models.CharField(max_length=500, null=True, blank=True)  # noqa: DJ001
    value_boolean = models.BooleanField(null=True, blank=True)
    unit = models.CharField(max_length=8, choices=AttributeUnit.choices, blank=True, default="")
    is_published = models.BooleanField(default=False)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(condition=_ONE_TARGET, name="catalog_attrval_one_target"),
            models.CheckConstraint(
                condition=(
                    Q(
                        value_type=AttributeValueType.DECIMAL,
                        value_decimal__isnull=False,
                        value_text__isnull=True,
                        value_boolean__isnull=True,
                    )
                    | Q(
                        value_type=AttributeValueType.TEXT,
                        value_decimal__isnull=True,
                        value_text__isnull=False,
                        value_boolean__isnull=True,
                    )
                    | Q(
                        value_type=AttributeValueType.BOOLEAN,
                        value_decimal__isnull=True,
                        value_text__isnull=True,
                        value_boolean__isnull=False,
                    )
                ),
                name="catalog_attrval_typed_value",
            ),
            models.UniqueConstraint(
                fields=["definition", "product"],
                condition=Q(product__isnull=False),
                name="catalog_attrval_unique_product",
            ),
            models.UniqueConstraint(
                fields=["definition", "variant"],
                condition=Q(variant__isnull=False),
                name="catalog_attrval_unique_variant",
            ),
        ]

    def __str__(self) -> str:
        return str(self.id)

    def save(self, *args: Any, **kwargs: Any) -> None:
        definition = self.definition
        for name in ("value_type", "unit"):
            own, canonical = getattr(self, name), getattr(definition, name)
            if own and own != canonical:
                raise ValidationError(
                    {name: "Debe coincidir con la definición del atributo."}, code="mismatch"
                )
            setattr(self, name, canonical)
        super().save(*args, **kwargs)


class Media(OrganizationScopedModel):
    """Reference to a catalog image (path or https URL; never fetched by the API).

    Product-level media has ``variant = NULL``. Only APPROVED media is public.
    """

    same_organization_fields = ("product", "variant")

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="media")
    variant = models.ForeignKey(
        Variant, null=True, blank=True, on_delete=models.CASCADE, related_name="media"
    )
    url = models.CharField(max_length=500)
    alt_text = models.CharField(max_length=300)
    status = models.CharField(max_length=16, choices=MediaStatus.choices, default=MediaStatus.DRAFT)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            _choices_check("status", MediaStatus, "catalog_media_status_known"),
            models.CheckConstraint(
                condition=Q(url__regex=MEDIA_URL_PATTERN), name="catalog_media_url_format"
            ),
            models.UniqueConstraint(
                fields=["product", "url"],
                condition=Q(variant__isnull=True),
                name="catalog_media_unique_product_url",
            ),
            models.UniqueConstraint(
                fields=["variant", "url"],
                condition=Q(variant__isnull=False),
                name="catalog_media_unique_variant_url",
            ),
        ]

    def __str__(self) -> str:
        return str(self.id)

    def check_same_organization(self) -> None:
        super().check_same_organization()
        if self.variant is not None and self.variant.product_id != self.product_id:
            raise ValidationError(
                {"variant": "Debe pertenecer al mismo producto."}, code="cross_product"
            )


class SourceReference(OrganizationScopedModel):
    """Staff-only provenance of a product or variant record."""

    same_organization_fields = ("product", "variant")

    product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.CASCADE, related_name="source_references"
    )
    variant = models.ForeignKey(
        Variant, null=True, blank=True, on_delete=models.CASCADE, related_name="source_references"
    )
    source_name = models.CharField(max_length=120)
    external_id = models.CharField(max_length=120)
    source_url = models.CharField(max_length=500, blank=True, default="")
    observed_at = models.DateTimeField()
    is_synthetic = models.BooleanField(default=False)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(condition=_ONE_TARGET, name="catalog_source_one_target"),
            models.CheckConstraint(
                condition=Q(source_url="") | Q(source_url__regex=SOURCE_URL_PATTERN),
                name="catalog_source_url_https",
            ),
            models.UniqueConstraint(
                fields=["organization", "source_name", "external_id"],
                name="catalog_source_unique_external_id",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.source_name}:{self.external_id}"
