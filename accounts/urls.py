from django.urls import path
from accounts.views import (
    APIKeyListCreateView,
    APIKeyRevokeView,
    JWTTokenObtainPairView,
    JWTTokenRefreshView,
    RegisterView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", JWTTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path(
        "auth/token/refresh/",
        JWTTokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path("api-keys/", APIKeyListCreateView.as_view(), name="api-key-list-create"),
    path(
        "api-keys/<uuid:api_key_id>/revoke/",
        APIKeyRevokeView.as_view(),
        name="api-key-revoke",
    ),
]
