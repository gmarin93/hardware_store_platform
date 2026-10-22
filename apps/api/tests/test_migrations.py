import pytest
from django.core.management import call_command
from django.db import connection


@pytest.mark.django_db
def test_migrations_are_complete_and_applied() -> None:
    # Raises SystemExit(1) if models and migrations diverge.
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)
    tables = set(connection.introspection.table_names())
    assert {
        "accounts_user",
        "accounts_customerprofile",
        "organizations_organization",
        "organizations_branch",
        "organizations_branchmembership",
        "organizations_roleassignment",
    } <= tables
