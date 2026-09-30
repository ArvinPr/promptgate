from dataclasses import asdict

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gateway import services
from gateway.authentication import APIKeyAuthentication
from gateway.providers.exceptions import ProviderConfigurationError, ProviderError
from gateway.rate_limits import (
    RateLimitExceeded,
    RateLimitServiceError,
    get_rate_limiter,
)
from gateway.serializers import GenerateRequestSerializer, GenerateResponseSerializer


class GenerateView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = GenerateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        try:
            get_rate_limiter().check(request.auth.pk)
        except RateLimitExceeded as exc:
            return Response(
                {
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Rate limit exceeded.",
                        "retry_after_seconds": exc.retry_after_seconds,
                    }
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(exc.retry_after_seconds)},
            )
        except RateLimitServiceError:
            return Response(
                {
                    "error": {
                        "code": "rate_limit_unavailable",
                        "message": "Rate limiting service is temporarily unavailable.",
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            result = services.generate(
                request_serializer.validated_data["prompt"],
                request.auth,
            )
        except ProviderConfigurationError as exc:
            return Response(
                {
                    "error": {
                        "code": "provider_not_configured",
                        "message": "The generation provider is not configured.",
                    },
                    "request_id": exc.request_id,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ProviderError as exc:
            return Response(
                {
                    "error": {
                        "code": "provider_error",
                        "message": "The generation provider is temporarily unavailable.",
                    },
                    "request_id": exc.request_id,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response_serializer = GenerateResponseSerializer(asdict(result))
        return Response(response_serializer.data)
