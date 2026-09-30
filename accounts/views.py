from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.models import APIKey
from accounts.serializers import (
    APIKeyCreatedSerializer,
    APIKeySerializer,
    RegistrationSerializer,
)


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register an account",
        request=RegistrationSerializer,
        responses={201: RegistrationSerializer},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            RegistrationSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class APIKeyListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List client API keys",
        responses={200: APIKeySerializer(many=True)},
        tags=["API keys"],
    )
    def get(self, request):
        api_keys = APIKey.objects.filter(user=request.user)
        return Response(APIKeySerializer(api_keys, many=True).data)

    @extend_schema(
        summary="Create a client API key",
        request=APIKeySerializer,
        responses={201: APIKeyCreatedSerializer},
        tags=["API keys"],
    )
    def post(self, request):
        serializer = APIKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        api_key, raw_key = APIKey.objects.create_key(
            user=request.user,
            name=serializer.validated_data["name"],
        )
        response_data = APIKeyCreatedSerializer(api_key).data
        response_data["key"] = raw_key
        return Response(response_data, status=status.HTTP_201_CREATED)


class APIKeyRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Revoke a client API key",
        request=None,
        responses={200: APIKeySerializer},
        tags=["API keys"],
    )
    def post(self, request, api_key_id):
        api_key = get_object_or_404(
            APIKey,
            id=api_key_id,
            user=request.user,
        )
        api_key.revoke()
        return Response(APIKeySerializer(api_key).data)


@extend_schema_view(
    post=extend_schema(
        summary="Obtain JWT access and refresh tokens",
        tags=["Authentication"],
    )
)
class JWTTokenObtainPairView(TokenObtainPairView):
    pass


@extend_schema_view(
    post=extend_schema(summary="Refresh a JWT access token", tags=["Authentication"])
)
class JWTTokenRefreshView(TokenRefreshView):
    pass
