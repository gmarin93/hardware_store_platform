"""Liveness and database connectivity endpoint.

Connectivity only: it does not touch any table, so it works before the first
migration exists.
"""

import logging

from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def database_is_reachable() -> bool:
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row: tuple[object, ...] | None = cursor.fetchone()
    except DatabaseError:
        # Log the failure class only; connection errors may embed host details.
        logger.warning("Health check: database unreachable")
        return False
    return bool(row == (1,))


class HealthView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="health_retrieve",
        responses={
            200: inline_serializer(
                name="Health",
                fields={
                    "status": serializers.CharField(),
                    "database": serializers.CharField(),
                },
            ),
            503: inline_serializer(
                name="HealthUnavailable",
                fields={
                    "status": serializers.CharField(),
                    "database": serializers.CharField(),
                },
            ),
        },
    )
    def get(self, request: Request) -> Response:
        if database_is_reachable():
            return Response({"status": "ok", "database": "ok"})
        return Response(
            {"status": "unavailable", "database": "unreachable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
