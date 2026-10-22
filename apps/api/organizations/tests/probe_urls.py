"""Test-only URLconf, never mounted in ``config.urls``.

* A visible-object action that needs ``staff.manage``. P1-02A ships no
  management endpoint; this probe exercises the shared helpers (scoped selector
  -> 404, then ``require_perm`` -> 403) exactly as real services must use them.
* A DRF view that raises unexpectedly (500 INTERNAL_ERROR path).
* A plain Django view protected by CsrfViewMiddleware (CSRF_FAILURE_VIEW path).
"""

import uuid

from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern, URLResolver, path
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import Perm
from common.permissions import require_perm
from config import urls as project_urls
from organizations.scope import get_request_actor, get_visible_branch


class BranchManageProbeView(APIView):
    def post(self, request: Request, branch_id: uuid.UUID) -> Response:
        actor = get_request_actor(request)
        get_visible_branch(actor, branch_id)
        require_perm(actor, Perm.STAFF_MANAGE)
        return Response(status=204)


class ExplodingView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        raise RuntimeError("detalle interno con correo persona@example.test")


def plain_django_post(request: HttpRequest) -> HttpResponse:
    return HttpResponse(status=204)


PROBE_PATH = "/api/v1/test-probe/branches/{}/manage"
EXPLODE_PATH = "/api/v1/test-probe/explode"
PLAIN_PATH = "/api/v1/test-probe/plain"

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/v1/test-probe/branches/<uuid:branch_id>/manage", BranchManageProbeView.as_view()),
    path("api/v1/test-probe/explode", ExplodingView.as_view()),
    path("api/v1/test-probe/plain", plain_django_post),
    *project_urls.urlpatterns,
]

handler404 = project_urls.handler404
handler500 = project_urls.handler500
