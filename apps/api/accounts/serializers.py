"""Auth request/response serializers. Passwords are write-only and never echoed."""

from typing import Any

from rest_framework import serializers

from organizations.scope import Actor, visible_branches


class LoginSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        max_length=256, write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )


class MeUserSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    full_name = serializers.CharField()


class MeOrganizationSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    slug = serializers.SlugField()
    name = serializers.CharField()
    is_synthetic = serializers.BooleanField()


class MeBranchSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()


class MeSerializer(serializers.Serializer[Any]):
    user = MeUserSerializer()
    organization = MeOrganizationSerializer(allow_null=True)
    role = serializers.ChoiceField(choices=["GUEST", "CUSTOMER", "EMPLOYEE", "ADMIN"])
    branches = MeBranchSerializer(many=True)
    permissions = serializers.ListField(child=serializers.CharField())


def me_payload(user: Any, actor: Actor) -> dict[str, Any]:
    branches = visible_branches(actor).order_by("name", "id")
    org = actor.organization
    return {
        "user": {"id": user.pk, "email": user.email, "full_name": user.full_name},
        "organization": (
            {"id": org.id, "slug": org.slug, "name": org.name, "is_synthetic": org.is_synthetic}
            if org is not None
            else None
        ),
        "role": actor.role.value,
        "branches": [{"id": b.id, "code": b.code, "name": b.name} for b in branches],
        "permissions": sorted(str(code) for code in actor.permissions),
    }
