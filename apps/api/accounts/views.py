"""Session auth endpoints: csrf, login, logout, me (ADR 0001/0003)."""

import logging

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import LoginSerializer, MeSerializer, me_payload
from accounts.throttling import LoginAccountThrottle, LoginIPThrottle
from common.authentication import EnforceCsrfMixin
from common.errors import InvalidCredentials
from common.schema import error_responses
from organizations.scope import get_request_actor, resolve_actor

logger = logging.getLogger(__name__)


class CsrfView(APIView):
    """Sets the CSRF cookie (readable by JS, sent back as ``X-CSRFToken``)."""

    permission_classes = (AllowAny,)

    @extend_schema(operation_id="auth_csrf_retrieve", responses={204: None})
    def get(self, request: Request) -> Response:
        get_token(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginView(EnforceCsrfMixin, APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (LoginIPThrottle, LoginAccountThrottle)

    @extend_schema(
        operation_id="auth_login_create",
        request=LoginSerializer,
        responses={200: MeSerializer, **error_responses(400, 403, 429)},
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request._request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        # Unknown email, wrong password and inactive users are indistinguishable;
        # ModelBackend hashes a dummy password for unknown users (timing).
        if user is None:
            logger.info("Login rejected")
            raise InvalidCredentials()
        login(request._request, user)  # rotates session key and CSRF token
        logger.info("Login succeeded for user %s", user.pk)
        return Response(me_payload(user, resolve_actor(user)))


class LogoutView(EnforceCsrfMixin, APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="auth_logout_create",
        request=None,
        responses={204: None, **error_responses(403)},
    )
    def post(self, request: Request) -> Response:
        logout(request._request)  # flushes the session
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="auth_me_retrieve",
        responses={200: MeSerializer, **error_responses(401)},
    )
    def get(self, request: Request) -> Response:
        return Response(me_payload(request.user, get_request_actor(request)))
