"""Composite foreign keys that keep related catalog rows in one organization.

Django cannot declare multi-column foreign keys, so they are added with SQL.
Each references a ``UniqueConstraint`` declared on the model in 0001
(``(id, organization)``, ``(id, product)`` or ``(id, value_type, unit)``).
They are checked immediately (not deferred), so cross-organization writes fail
at the statement, including bulk ``update()`` and raw SQL that bypass ``save()``.
"""

from django.db import migrations

# (constraint name, table, columns, referenced table, referenced columns, ON UPDATE)
COMPOSITE_FOREIGN_KEYS = [
    ("catalog_category_parent_same_org", "catalog_category", "parent_id, organization_id", "catalog_category", "id, organization_id", "NO ACTION"),
    ("catalog_product_brand_same_org", "catalog_product", "brand_id, organization_id", "catalog_brand", "id, organization_id", "NO ACTION"),
    ("catalog_product_category_same_org", "catalog_product", "category_id, organization_id", "catalog_category", "id, organization_id", "NO ACTION"),
    ("catalog_variant_product_same_org", "catalog_variant", "product_id, organization_id", "catalog_product", "id, organization_id", "NO ACTION"),
    ("catalog_attrval_definition_same_org", "catalog_attributevalue", "definition_id, organization_id", "catalog_attributedefinition", "id, organization_id", "NO ACTION"),
    # The value's type and unit always equal its definition's.
    ("catalog_attrval_definition_type_unit", "catalog_attributevalue", "definition_id, value_type, unit", "catalog_attributedefinition", "id, value_type, unit", "CASCADE"),
    ("catalog_attrval_product_same_org", "catalog_attributevalue", "product_id, organization_id", "catalog_product", "id, organization_id", "NO ACTION"),
    ("catalog_attrval_variant_same_org", "catalog_attributevalue", "variant_id, organization_id", "catalog_variant", "id, organization_id", "NO ACTION"),
    ("catalog_media_product_same_org", "catalog_media", "product_id, organization_id", "catalog_product", "id, organization_id", "NO ACTION"),
    # Variant-level media belongs to a variant of the same product.
    ("catalog_media_variant_same_product", "catalog_media", "variant_id, product_id", "catalog_variant", "id, product_id", "NO ACTION"),
    ("catalog_source_product_same_org", "catalog_sourcereference", "product_id, organization_id", "catalog_product", "id, organization_id", "NO ACTION"),
    ("catalog_source_variant_same_org", "catalog_sourcereference", "variant_id, organization_id", "catalog_variant", "id, organization_id", "NO ACTION"),
]


def _add(name, table, columns, ref_table, ref_columns, on_update):
    return (
        f"ALTER TABLE {table} ADD CONSTRAINT {name} FOREIGN KEY ({columns}) "
        f"REFERENCES {ref_table} ({ref_columns}) ON DELETE NO ACTION ON UPDATE {on_update}"
    )


def _drop(name, table, *_):
    return f"ALTER TABLE {table} DROP CONSTRAINT {name}"


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [
        migrations.RunSQL(sql=_add(*fk), reverse_sql=_drop(*fk)) for fk in COMPOSITE_FOREIGN_KEYS
    ]
