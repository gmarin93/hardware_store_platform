from django.urls import URLPattern, path

from organizations import views

# ``str`` (not ``uuid``) converter: malformed ids reach the view and get the
# same DRF NotFound response (body and headers) as nonexistent/out-of-scope ids.
urlpatterns: list[URLPattern] = [
    path("branches", views.BranchListView.as_view(), name="branch-list"),
    path("branches/<str:branch_id>", views.BranchDetailView.as_view(), name="branch-detail"),
]
