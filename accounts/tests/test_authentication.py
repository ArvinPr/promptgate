import pytest
from django.urls import reverse
from rest_framework import status

from accounts.models import User


@pytest.mark.django_db
def test_user_can_register(api_client):
    response = api_client.post(
        reverse("register"),
        {"email": "New.User@Example.COM", "password": "StrongPass123!"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {
        "id": response.json()["id"],
        "email": "new.user@example.com",
    }

    user = User.objects.get(email="new.user@example.com")
    assert user.check_password("StrongPass123!")
    assert user.password != "StrongPass123!"


@pytest.mark.django_db
def test_user_can_obtain_and_refresh_jwt(api_client, user):
    token_response = api_client.post(
        reverse("token_obtain_pair"),
        {"email": user.email, "password": "StrongPass123!"},
        format="json",
    )

    assert token_response.status_code == status.HTTP_200_OK
    assert token_response.json()["access"]
    assert token_response.json()["refresh"]

    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {token_response.json()['access']}"
    )
    authenticated_response = api_client.get(reverse("api-key-list-create"))
    assert authenticated_response.status_code == status.HTTP_200_OK

    refresh_response = api_client.post(
        reverse("token_refresh"),
        {"refresh": token_response.json()["refresh"]},
        format="json",
    )

    assert refresh_response.status_code == status.HTTP_200_OK
    assert refresh_response.json()["access"]
