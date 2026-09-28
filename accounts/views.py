from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import APIKey
from accounts.serializers import (
    APIKeyCreatedSerializer,
    APIKeySerializer,
    RegistrationSerializer,
)


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

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

    def get(self, request):
        api_keys = APIKey.objects.filter(user=request.user)
        return Response(APIKeySerializer(api_keys, many=True).data)

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

    def post(self, request, api_key_id):
        api_key = get_object_or_404(
            APIKey,
            id=api_key_id,
            user=request.user,
        )
        api_key.revoke()
        return Response(APIKeySerializer(api_key).data)
