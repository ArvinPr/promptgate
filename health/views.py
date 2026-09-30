from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Check service health",
        responses={200: OpenApiResponse(description="Service is healthy.")},
        tags=["Health"],
    )
    def get(self, request):
        return Response({"status": "ok"})
