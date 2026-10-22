"""Actor resolution and scoped selectors (ADR 0001/0003).

Scope is recomputed from the database on every request from *active* rows
only: active user, active organization, active branch, active membership or
role assignment. Nothing is taken from serializers, the session payload or a
client-supplied ``branch_id`` (which is only a selector, validated here).

Role resolution (fail closed):
1. Collect the organizations of the user's active ADMIN assignments, active
   branch memberships and customer profile.
2. If there is not exactly one such organization, the user has no business
   role and is treated as GUEST (an ambiguous multi-organization account
   grants nothing; it is logged by user id only).
3. ADMIN > EMPLOYEE > CUSTOMER within that organization.

``is_superuser``/``is_staff`` are ignored.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.db.models import Model, QuerySet
from django.http import HttpRequest
from rest_framework.exceptions import NotFound
from rest_framework.request import Request

from accounts.models import CustomerProfile
from accounts.permissions import Perm, Role, permissions_for
from organizations.models import Branch, BranchMembership, Organization, RoleAssignment

logger = logging.getLogger(__name__)

_ACTOR_ATTR = "_scoped_actor"


@dataclass(frozen=True)
class Actor:
    user_id: uuid.UUID | None
    role: Role
    organization: Organization | None
    branch_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)
    permissions: frozenset[Perm] = field(default_factory=frozenset)

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None

    @property
    def organization_id(self) -> uuid.UUID | None:
        return self.organization.id if self.organization is not None else None

    def has_perm(self, code: Perm | str) -> bool:
        return code in self.permissions


def default_organization() -> Organization | None:
    slug = settings.DEFAULT_ORGANIZATION_SLUG
    return Organization.objects.filter(slug=slug, is_active=True).first()


def _guest(user_id: uuid.UUID | None) -> Actor:
    return Actor(
        user_id=user_id,
        role=Role.GUEST,
        organization=default_organization(),
        permissions=permissions_for(Role.GUEST),
    )


def resolve_actor(user: Any) -> Actor:
    """Build the actor for ``user`` (a User or AnonymousUser) from active rows."""
    if user is None or not user.is_authenticated or not user.is_active:
        return _guest(None)
    user_id: uuid.UUID = user.pk

    admin_org_ids = set(
        RoleAssignment.objects.filter(
            user_id=user_id,
            is_active=True,
            role=RoleAssignment.RoleName.ADMIN,
            organization__is_active=True,
        ).values_list("organization_id", flat=True)
    )
    memberships = list(
        BranchMembership.objects.filter(
            user_id=user_id,
            is_active=True,
            branch__is_active=True,
            branch__organization__is_active=True,
        ).values_list("branch_id", "branch__organization_id")
    )
    customer_org_ids = set(
        CustomerProfile.objects.filter(user_id=user_id, organization__is_active=True).values_list(
            "organization_id", flat=True
        )
    )
    candidates = admin_org_ids | {org for _, org in memberships} | customer_org_ids
    if len(candidates) != 1:
        if len(candidates) > 1:
            logger.warning("Account %s spans several organizations; no role granted.", user_id)
        return _guest(user_id)

    (org_id,) = candidates
    organization = Organization.objects.get(pk=org_id)
    if org_id in admin_org_ids:
        role = Role.ADMIN
        branch_ids = frozenset(
            Branch.objects.filter(organization_id=org_id, is_active=True).values_list(
                "id", flat=True
            )
        )
    elif memberships:
        role = Role.EMPLOYEE
        branch_ids = frozenset(branch_id for branch_id, _ in memberships)
    else:
        role = Role.CUSTOMER
        branch_ids = frozenset()
    return Actor(
        user_id=user_id,
        role=role,
        organization=organization,
        branch_ids=branch_ids,
        permissions=permissions_for(role),
    )


def get_request_actor(request: Request | HttpRequest) -> Actor:
    """Resolve once per request; never reused across requests."""
    http_request: HttpRequest = getattr(request, "_request", request)
    cached = getattr(http_request, _ACTOR_ATTR, None)
    if isinstance(cached, Actor) and cached.user_id == getattr(request.user, "pk", None):
        return cached
    actor = resolve_actor(request.user)
    setattr(http_request, _ACTOR_ATTR, actor)
    return actor


# --- Scoped selectors -------------------------------------------------------


def visible_branches(actor: Actor) -> QuerySet[Branch]:
    """Branches whose staff data the actor may see (empty for customers/guests)."""
    if actor.organization is None:
        return Branch.objects.none()
    base = Branch.objects.filter(organization_id=actor.organization.id, is_active=True)
    if actor.has_perm(Perm.BRANCHES_VIEW_ALL):
        return base
    if actor.has_perm(Perm.BRANCHES_VIEW_ASSIGNED):
        return base.filter(id__in=actor.branch_ids)
    return Branch.objects.none()


def parse_uuid(raw: object) -> uuid.UUID | None:
    if isinstance(raw, uuid.UUID):
        return raw
    if not isinstance(raw, str):
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


def get_visible_branch(actor: Actor, branch_id: object) -> Branch:
    """Resolve a client-supplied branch selector or raise NotFound.

    Malformed, nonexistent, other-organization and non-member branches all
    produce the same 404 NOT_FOUND.
    """
    parsed = parse_uuid(branch_id)
    if parsed is None:
        raise NotFound()
    branch = visible_branches(actor).filter(id=parsed).first()
    if branch is None:
        raise NotFound()
    return branch


def scope_to_organization[M: Model](
    queryset: QuerySet[M], actor: Actor, field_name: str = "organization"
) -> QuerySet[M]:
    """Restrict ``queryset`` to the actor's organization (none if no organization)."""
    if actor.organization is None:
        return queryset.none()
    return queryset.filter(**{f"{field_name}_id": actor.organization.id})


def scope_to_visible_branches[M: Model](
    queryset: QuerySet[M], actor: Actor, field_name: str = "branch"
) -> QuerySet[M]:
    """Restrict ``queryset`` to rows whose ``field_name`` branch is visible."""
    return queryset.filter(**{f"{field_name}__in": visible_branches(actor)})


def get_scoped_object_or_404[M: Model](queryset: QuerySet[M], object_id: object) -> M:
    """Fetch from an already-scoped queryset; out-of-scope equals nonexistent."""
    parsed = parse_uuid(object_id)
    if parsed is None:
        raise NotFound()
    obj = queryset.filter(pk=parsed).first()
    if obj is None:
        raise NotFound()
    return obj
