"""Branch read endpoints. Querysets are always derived from the request actor."""

from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics

from common.schema import error_responses
from organizations.models import Branch
from organizations.scope import get_request_actor, get_visible_branch, visible_branches
from organizations.serializers import BranchSerializer


@extend_schema_view(
    get=extend_schema(
        operation_id="branches_list",
        responses={200: BranchSerializer(many=True), **error_responses(400, 401)},
    )
)
class BranchListView(generics.ListAPIView[Branch]):
    """Branches visible to the actor (silently filtered; customers get [])."""

    serializer_class = BranchSerializer
    cursor_ordering = ("name", "id")

    def get_queryset(self) -> QuerySet[Branch]:
        return visible_branches(get_request_actor(self.request))


@extend_schema_view(
    get=extend_schema(
        operation_id="branches_retrieve",
        parameters=[OpenApiParameter("branch_id", OpenApiTypes.UUID, OpenApiParameter.PATH)],
        responses={200: BranchSerializer, **error_responses(401, 404)},
    )
)
class BranchDetailView(generics.RetrieveAPIView[Branch]):
    """Invisible, other-organization and nonexistent branches are the same 404."""

    serializer_class = BranchSerializer

    def get_queryset(self) -> QuerySet[Branch]:
        return visible_branches(get_request_actor(self.request))

    def get_object(self) -> Branch:
        return get_visible_branch(get_request_actor(self.request), self.kwargs["branch_id"])
