from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from accounts.models import APIKey


class APIKeyAuthentication(BaseAuthentication):
    keyword = b"api-key"

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != self.keyword:
            return None

        if len(parts) != 2:
            raise AuthenticationFailed("Invalid API key.")

        try:
            raw_key = parts[1].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AuthenticationFailed("Invalid API key.") from exc

        key_hash = APIKey.objects.hash_key(raw_key)
        api_key = (
            APIKey.objects.select_related("user")
            .filter(key_hash=key_hash)
            .first()
        )

        if api_key is None or not api_key.user.is_active:
            raise AuthenticationFailed("Invalid API key.")
        if not api_key.is_active:
            raise AuthenticationFailed("API key has been revoked.")

        used_at = timezone.now()
        APIKey.objects.filter(pk=api_key.pk).update(last_used_at=used_at)
        api_key.last_used_at = used_at
        return api_key.user, api_key

    def authenticate_header(self, request):
        return "Api-Key"
