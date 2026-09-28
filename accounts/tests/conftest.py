import pytest
from rest_framework.test import APIClient

from accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="owner@example.com",
        password="StrongPass123!",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client
