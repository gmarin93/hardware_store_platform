from typing import Any

from rest_framework import serializers

from organizations.models import Branch


class BranchSerializer(serializers.ModelSerializer[Branch]):
    class Meta:
        model = Branch
        fields: Any = ("id", "code", "name", "organization")
        read_only_fields = fields
