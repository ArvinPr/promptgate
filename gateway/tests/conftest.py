import pytest
from rest_framework.test import APIClient

from accounts.models import APIKey, User


@pytest.fixture
def gateway_credentials(db):
    user = User.objects.create_user(
        email="gateway@example.com",
        password="StrongPass123!",
    )
    api_key, raw_key = APIKey.objects.create_key(user=user, name="Gateway tests")
    return user, api_key, raw_key


@pytest.fixture
def api_key_client(gateway_credentials):
    _, _, raw_key = gateway_credentials
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {raw_key}")
    return client
