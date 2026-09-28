from dataclasses import asdict

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gateway import services
from gateway.authentication import APIKeyAuthentication
from gateway.providers.exceptions import ProviderConfigurationError, ProviderError
from gateway.serializers import GenerateRequestSerializer, GenerateResponseSerializer


class GenerateView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = GenerateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        try:
            result = services.generate(request_serializer.validated_data["prompt"])
        except ProviderConfigurationError:
            return Response(
                {
                    "error": {
                        "code": "provider_not_configured",
                        "message": "The generation provider is not configured.",
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ProviderError:
            return Response(
                {
                    "error": {
                        "code": "provider_error",
                        "message": "The generation provider is temporarily unavailable.",
                    }
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response_serializer = GenerateResponseSerializer(asdict(result))
        return Response(response_serializer.data)
