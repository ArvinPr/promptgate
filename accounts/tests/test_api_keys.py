import pytest
from django.urls import reverse
from rest_framework import status

from accounts.models import APIKey, User


@pytest.mark.django_db
def test_authenticated_user_can_create_api_key(authenticated_client, user):
    response = authenticated_client.post(
        reverse("api-key-list-create"),
        {"name": "Local development"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == "Local development"
    assert response.json()["key"].startswith("pg_")
    assert response.json()["prefix"] == response.json()["key"][:11]
    assert response.json()["active"] is True
    assert APIKey.objects.get().user == user


@pytest.mark.django_db
def test_raw_api_key_is_never_stored(authenticated_client):
    response = authenticated_client.post(
        reverse("api-key-list-create"),
        {"name": "Production"},
        format="json",
    )
    raw_key = response.json()["key"]
    stored_key = APIKey.objects.get()

    assert stored_key.key_hash != raw_key
    assert len(stored_key.key_hash) == 64
    assert raw_key not in str(stored_key.__dict__.values())


@pytest.mark.django_db
def test_user_can_list_only_key_metadata(authenticated_client):
    create_response = authenticated_client.post(
        reverse("api-key-list-create"),
        {"name": "CLI"},
        format="json",
    )

    response = authenticated_client.get(reverse("api-key-list-create"))

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == create_response.json()["id"]
    assert response.json()[0]["name"] == "CLI"
    assert "key" not in response.json()[0]
    assert "key_hash" not in response.json()[0]


@pytest.mark.django_db
def test_user_can_revoke_api_key(authenticated_client, user):
    api_key, _ = APIKey.objects.create_key(user=user, name="Old integration")

    response = authenticated_client.post(
        reverse("api-key-revoke", kwargs={"api_key_id": api_key.id})
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False
    api_key.refresh_from_db()
    assert api_key.revoked_at is not None


@pytest.mark.django_db
def test_users_cannot_list_or_revoke_another_users_keys(api_client, user):
    other_user = User.objects.create_user(
        email="other@example.com",
        password="AnotherStrongPass123!",
    )
    other_key, _ = APIKey.objects.create_key(user=other_user, name="Private")
    own_key, _ = APIKey.objects.create_key(user=user, name="Mine")
    api_client.force_authenticate(user=user)

    list_response = api_client.get(reverse("api-key-list-create"))
    revoke_response = api_client.post(
        reverse("api-key-revoke", kwargs={"api_key_id": other_key.id})
    )

    assert [item["id"] for item in list_response.json()] == [str(own_key.id)]
    assert revoke_response.status_code == status.HTTP_404_NOT_FOUND
    other_key.refresh_from_db()
    assert other_key.revoked_at is None


@pytest.mark.django_db
def test_api_key_endpoints_require_authentication(api_client):
    response = api_client.get(reverse("api-key-list-create"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
