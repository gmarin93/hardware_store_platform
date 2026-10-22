"""Organization, branch, branch membership (EMPLOYEE) and role assignment (ADMIN)."""

import uuid
from typing import ClassVar

from django.conf import settings
from django.db import models


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    # True for demonstration/test fixtures; such data is never real store data.
    is_synthetic = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self) -> str:
        return self.slug


class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="branches"
    )
    code = models.SlugField(max_length=32)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="organizations_branch_unique_code"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization_id}:{self.code}"


class BranchMembership(models.Model):
    """An active membership makes the user an EMPLOYEE of that branch."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="branch_memberships"
    )
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="memberships")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["user", "branch"], name="organizations_membership_unique_user_branch"
            ),
        ]

    def __str__(self) -> str:
        return str(self.id)


class RoleAssignment(models.Model):
    """Organization-level role. ADMIN covers every branch of that organization only."""

    class RoleName(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="role_assignments"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="role_assignments"
    )
    role = models.CharField(max_length=16, choices=RoleName.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["user", "organization", "role"],
                name="organizations_role_unique_user_org_role",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=["ADMIN"]), name="organizations_role_known"
            ),
        ]

    def __str__(self) -> str:
        return str(self.id)
