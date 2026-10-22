"""Root URL configuration.

Only the versioned API is mounted. Django admin is intentionally not mounted
(ADR 0001). Later tasks add their routes to ``api_v1_patterns``.
"""

from django.urls import URLPattern, URLResolver, include, path, re_path

from common.views import api_not_found
from config.health import HealthView

api_v1_patterns: list[URLPattern | URLResolver] = [
    path("health", HealthView.as_view(), name="health"),
    path("", include("accounts.urls")),
    path("", include("organizations.urls")),
    path("", include("catalog.urls")),
    # Later tasks add their includes above this comment.
    # Must stay last: unknown API paths get the JSON NOT_FOUND envelope.
    re_path(r"^.*$", api_not_found, name="not-found"),
]

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/v1/", include((api_v1_patterns, "api_v1"), namespace="v1")),
]

handler404 = "common.views.handler404"
handler500 = "common.views.handler500"
