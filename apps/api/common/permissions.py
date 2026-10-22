"""Shared permission helpers based on permission codes (ADR 0003).

Order of checks inside a view/service:
1. Authentication (401 NOT_AUTHENTICATED) via DRF permission classes.
2. Scoped lookup: anything outside the actor's scope is 404 NOT_FOUND.
3. ``require_perm`` on the visible object: 403 PERMISSION_DENIED.
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.permissions import Perm
from organizations.scope import Actor, get_request_actor


def require_perm(actor: Actor, code: Perm) -> None:
    if not actor.has_perm(code):
        raise PermissionDenied()


class HasPermissionCodes(BasePermission):
    """Authenticated and holding every code in ``view.required_permissions``.

    Anonymous requests fail as NOT_AUTHENTICATED (401). Use only where a
    missing code should be 403 rather than an empty/404 scoped result.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        required: frozenset[Perm] = getattr(view, "required_permissions", frozenset())
        actor = get_request_actor(request)
        return all(actor.has_perm(code) for code in required)
