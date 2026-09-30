from unittest.mock import Mock, patch

import pytest
from rest_framework.test import APIClient

from accounts.models import APIKey, User
from gateway.rate_limits import RateLimitStatus


@pytest.fixture(autouse=True)
def rate_limiter():
    limiter = Mock()
    limiter.check.return_value = RateLimitStatus(
        limit=60,
        remaining=59,
        retry_after_seconds=60,
    )
    with patch("gateway.views.get_rate_limiter", return_value=limiter):
        yield limiter


@pytest.fixture(autouse=True)
def response_cache():
    cache = Mock()
    cache.get.return_value = None
    with patch("gateway.services.get_response_cache", return_value=cache):
        yield cache


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
