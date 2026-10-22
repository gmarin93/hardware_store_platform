"""Identity: email-login user and customer profile (ADR 0001/0003).

``is_superuser``/``is_staff`` exist only for Django compatibility; they grant
no business permission and no cross-organization access.
"""

import uuid
from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower


def normalize_email(email: str) -> str:
    return email.strip().lower()


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> "User":
        if not email:
            raise ValueError("Email is required.")
        user = self.model(email=normalize_email(email), **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> "User":
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)

    def get_by_natural_key(self, username: str | None) -> "User":
        return self.get(email=normalize_email(username or ""))


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=254)
    full_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(email=Lower("email")), name="accounts_user_email_lowercase"
            ),
        ]

    def __str__(self) -> str:
        return str(self.id)

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = normalize_email(self.email)
        super().save(*args, **kwargs)


class CustomerProfile(models.Model):
    """Marks a user as a CUSTOMER of one organization (no branch)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile")
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="customer_profiles"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self) -> str:
        return str(self.id)
