"""Catalog read endpoints (GET only). Querysets always come from ``catalog.selectors``.

Public endpoints (``/catalog/products``, ``/catalog/variants``) allow anyone and
always use the public serializers, whatever the caller's role: unpublished,
archived, other-organization, malformed and nonexistent ids are the same 404.

Staff endpoints (``/catalog/staff/...``) are the explicit staff view: they need
an authenticated actor holding ``catalog.view_staff_fields`` (401 if
anonymous, 403 otherwise, checked before any lookup so a 403 never depends on
the id), then the scoped lookup inside the actor's organization (404).
"""

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from accounts.permissions import Perm
from catalog import selectors
from catalog.models import Product, Variant
from catalog.serializers import (
    ProductQuerySerializer,
    PublicProductDetailSerializer,
    PublicProductSerializer,
    PublicVariantDetailSerializer,
    SkuQuerySerializer,
    StaffProductDetailSerializer,
    StaffProductQuerySerializer,
    StaffProductSerializer,
    StaffVariantDetailSerializer,
)
from common.permissions import HasPermissionCodes
from common.schema import ErrorEnvelopeSerializer, error_responses
from organizations.scope import Actor, get_request_actor, get_scoped_object_or_404

# Public cursors may only carry public values (cursors are signed, not encrypted).
PRODUCT_ORDERING = ("name", "id")
VARIANT_ORDERING = ("sku", "id")

_PUBLIC = ["Catálogo"]
_STAFF = ["Catálogo (personal)"]


# Narrower than common.schema's generic 400 text (no credentials on these endpoints).
_BAD_QUERY = {
    400: OpenApiResponse(
        response=ErrorEnvelopeSerializer,
        description="VALIDATION_ERROR (parámetros de consulta) o INVALID_CURSOR",
    )
}


def _path_id(name: str) -> OpenApiParameter:
    return OpenApiParameter(name, OpenApiTypes.UUID, OpenApiParameter.PATH)


class _CatalogView(APIView):
    def actor(self) -> Actor:
        return get_request_actor(self.request)

    def query(self, serializer_class: type[BaseSerializer[Any]]) -> dict[str, Any]:
        params = serializer_class(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return dict(params.validated_data)


class _PublicView(_CatalogView):
    permission_classes = (AllowAny,)


class _StaffView(_CatalogView):
    permission_classes = (HasPermissionCodes,)
    required_permissions = frozenset({Perm.CATALOG_VIEW_STAFF_FIELDS})


# --- Public -----------------------------------------------------------------------


@extend_schema_view(
    get=extend_schema(
        operation_id="catalog_products_list",
        tags=_PUBLIC,
        summary="Productos publicados",
        parameters=[ProductQuerySerializer],
        responses={200: PublicProductSerializer(many=True), **_BAD_QUERY},
    )
)
class PublicProductListView(_PublicView, generics.ListAPIView[Product]):
    # Schema generation only; requests always use get_queryset().
    queryset = Product.objects.none()
    serializer_class = PublicProductSerializer
    cursor_ordering = PRODUCT_ORDERING

    def get_queryset(self) -> QuerySet[Product]:
        return selectors.filter_products(
            selectors.public_product_list(self.actor()), **self.query(ProductQuerySerializer)
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="catalog_products_retrieve",
        tags=_PUBLIC,
        summary="Producto publicado con sus variantes publicadas",
        parameters=[_path_id("product_id")],
        responses={200: PublicProductDetailSerializer, **error_responses(404)},
    )
)
class PublicProductDetailView(_PublicView, generics.RetrieveAPIView[Product]):
    # Schema generation only; requests always use get_queryset().
    queryset = Product.objects.none()
    serializer_class = PublicProductDetailSerializer

    def get_queryset(self) -> QuerySet[Product]:
        return selectors.public_product_detail(self.actor())

    def get_object(self) -> Product:
        return get_scoped_object_or_404(self.get_queryset(), self.kwargs["product_id"])


@extend_schema_view(
    get=extend_schema(
        operation_id="catalog_variants_list",
        tags=_PUBLIC,
        summary="Variante publicada por SKU exacto",
        parameters=[SkuQuerySerializer],
        responses={200: PublicVariantDetailSerializer(many=True), **_BAD_QUERY},
    )
)
class PublicVariantListView(_PublicView, generics.ListAPIView[Variant]):
    """``sku`` is required in P1 (exact match; at most one result)."""

    # Schema generation only; requests always use get_queryset().
    queryset = Variant.objects.none()
    serializer_class = PublicVariantDetailSerializer
    cursor_ordering = VARIANT_ORDERING

    def get_queryset(self) -> QuerySet[Variant]:
        sku = self.query(SkuQuerySerializer)["sku"]
        return selectors.filter_variants_by_sku(selectors.public_variants(self.actor()), sku)


@extend_schema_view(
    get=extend_schema(
        operation_id="catalog_variants_retrieve",
        tags=_PUBLIC,
        summary="Variante publicada",
        parameters=[_path_id("variant_id")],
        responses={200: PublicVariantDetailSerializer, **error_responses(404)},
    )
)
class PublicVariantDetailView(_PublicView, generics.RetrieveAPIView[Variant]):
    # Schema generation only; requests always use get_queryset().
    queryset = Variant.objects.none()
    serializer_class = PublicVariantDetailSerializer

    def get_queryset(self) -> QuerySet[Variant]:
        return selectors.public_variants(self.actor())

    def get_object(self) -> Variant:
        return get_scoped_object_or_404(self.get_queryset(), self.kwargs["variant_id"])


# --- Staff ------------------------------------------------------------------------


@extend_schema_view(
    get=extend_schema(
        operation_id="catalog_staff_products_list",
        tags=_STAFF,
        summary="Productos de la organización en cualquier estado (personal)",
        parameters=[StaffProductQuerySerializer],
        responses={
            200: StaffProductSerializer(many=True),
            **_BAD_QUERY,
            **error_responses(401, 403),
        },
    )
)
class StaffProductListView(_StaffView, generics.ListAPIView[Product]):
    # Schema generation only; requests always use get_queryset().
    queryset = Product.objects.none()
    serializer_class = StaffProductSerializer
    cursor_ordering = PRODUCT_ORDERING

    def get_queryset(self) -> QuerySet[Product]:
        return selectors.filter_products(
            selectors.staff_product_list(self.actor()), **self.query(StaffProductQuerySerializer)
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="catalog_staff_products_retrieve",
        tags=_STAFF,
        summary="Producto con campos internos y procedencia (personal)",
        parameters=[_path_id("product_id")],
        responses={200: StaffProductDetailSerializer, **error_responses(401, 403, 404)},
    )
)
class StaffProductDetailView(_StaffView, generics.RetrieveAPIView[Product]):
    # Schema generation only; requests always use get_queryset().
    queryset = Product.objects.none()
    serializer_class = StaffProductDetailSerializer

    def get_queryset(self) -> QuerySet[Product]:
        return selectors.staff_product_detail(self.actor())

    def get_object(self) -> Product:
        return get_scoped_object_or_404(self.get_queryset(), self.kwargs["product_id"])


@extend_schema_view(
    get=extend_schema(
        operation_id="catalog_staff_variants_list",
        tags=_STAFF,
        summary="Variante por SKU exacto en cualquier estado (personal)",
        parameters=[SkuQuerySerializer],
        responses={
            200: StaffVariantDetailSerializer(many=True),
            **_BAD_QUERY,
            **error_responses(401, 403),
        },
    )
)
class StaffVariantListView(_StaffView, generics.ListAPIView[Variant]):
    # Schema generation only; requests always use get_queryset().
    queryset = Variant.objects.none()
    serializer_class = StaffVariantDetailSerializer
    cursor_ordering = VARIANT_ORDERING

    def get_queryset(self) -> QuerySet[Variant]:
        sku = self.query(SkuQuerySerializer)["sku"]
        return selectors.filter_variants_by_sku(selectors.staff_variants(self.actor()), sku)


@extend_schema_view(
    get=extend_schema(
        operation_id="catalog_staff_variants_retrieve",
        tags=_STAFF,
        summary="Variante con campos internos y procedencia (personal)",
        parameters=[_path_id("variant_id")],
        responses={200: StaffVariantDetailSerializer, **error_responses(401, 403, 404)},
    )
)
class StaffVariantDetailView(_StaffView, generics.RetrieveAPIView[Variant]):
    # Schema generation only; requests always use get_queryset().
    queryset = Variant.objects.none()
    serializer_class = StaffVariantDetailSerializer

    def get_queryset(self) -> QuerySet[Variant]:
        return selectors.staff_variants(self.actor())

    def get_object(self) -> Variant:
        return get_scoped_object_or_404(self.get_queryset(), self.kwargs["variant_id"])
