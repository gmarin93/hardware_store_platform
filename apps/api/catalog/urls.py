from django.urls import URLPattern, path

from catalog import views

# ``str`` (not ``uuid``) converters: malformed ids reach the view and get the
# same DRF NotFound response (body and headers) as nonexistent/hidden ids.
urlpatterns: list[URLPattern] = [
    path("catalog/products", views.PublicProductListView.as_view(), name="catalog-product-list"),
    path(
        "catalog/products/<str:product_id>",
        views.PublicProductDetailView.as_view(),
        name="catalog-product-detail",
    ),
    path("catalog/variants", views.PublicVariantListView.as_view(), name="catalog-variant-list"),
    path(
        "catalog/variants/<str:variant_id>",
        views.PublicVariantDetailView.as_view(),
        name="catalog-variant-detail",
    ),
    path(
        "catalog/staff/products",
        views.StaffProductListView.as_view(),
        name="catalog-staff-product-list",
    ),
    path(
        "catalog/staff/products/<str:product_id>",
        views.StaffProductDetailView.as_view(),
        name="catalog-staff-product-detail",
    ),
    path(
        "catalog/staff/variants",
        views.StaffVariantListView.as_view(),
        name="catalog-staff-variant-list",
    ),
    path(
        "catalog/staff/variants/<str:variant_id>",
        views.StaffVariantDetailView.as_view(),
        name="catalog-staff-variant-detail",
    ),
]
