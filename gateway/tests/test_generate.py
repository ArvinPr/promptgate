from unittest.mock import Mock, patch

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from gateway.providers.base import GenerationResult
from gateway.providers.exceptions import ProviderRequestError


@pytest.mark.django_db
def test_generate_requires_client_api_key():
    response = APIClient().post(
        reverse("generate"),
        {"prompt": "Hello"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == "Api-Key"


@pytest.mark.django_db
def test_generate_rejects_invalid_api_key():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Api-Key pg_invalid")

    response = client.post(
        reverse("generate"),
        {"prompt": "Hello"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid API key."}


@pytest.mark.django_db
def test_generate_rejects_revoked_api_key(api_key_client, gateway_credentials):
    _, api_key, _ = gateway_credentials
    api_key.revoke()

    response = api_key_client.post(
        reverse("generate"),
        {"prompt": "Hello"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "API key has been revoked."}


@pytest.mark.django_db
def test_generate_does_not_accept_jwt(gateway_credentials):
    user, _, _ = gateway_credentials
    access_token = str(RefreshToken.for_user(user).access_token)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    response = client.post(
        reverse("generate"),
        {"prompt": "Hello"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload, expected_message",
    [
        ({}, "This field is required."),
        ({"prompt": 123}, "Not a valid string."),
        ({"prompt": "   "}, "This field may not be blank."),
        ({"prompt": "x" * 10_001}, "Ensure this field has no more than 10000"),
    ],
)
def test_generate_validates_prompt(api_key_client, payload, expected_message):
    with patch("gateway.services.get_provider") as get_provider:
        response = api_key_client.post(reverse("generate"), payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert expected_message in response.json()["prompt"][0]
    get_provider.assert_not_called()


@pytest.mark.django_db
def test_generate_returns_normalized_provider_response(api_key_client):
    provider = Mock()
    provider.generate.return_value = GenerationResult(
        output="Database indexes are lookup shortcuts.",
        provider="gemini",
        model="gemini-test",
        request_id="request-123",
    )

    with patch("gateway.services.get_provider", return_value=provider):
        response = api_key_client.post(
            reverse("generate"),
            {"prompt": "Explain database indexes."},
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "output": "Database indexes are lookup shortcuts.",
        "provider": "gemini",
        "model": "gemini-test",
        "request_id": "request-123",
    }
    provider.generate.assert_called_once_with("Explain database indexes.")


@pytest.mark.django_db
def test_provider_failure_returns_clean_error(api_key_client):
    provider = Mock()
    provider.generate.side_effect = ProviderRequestError(
        "Internal SDK failure containing sensitive details"
    )

    with patch("gateway.services.get_provider", return_value=provider):
        response = api_key_client.post(
            reverse("generate"),
            {"prompt": "Hello"},
            format="json",
        )

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.json() == {
        "error": {
            "code": "provider_error",
            "message": "The generation provider is temporarily unavailable.",
        }
    }
    assert "sensitive" not in response.content.decode().lower()


@pytest.mark.django_db
@override_settings(GEMINI_API_KEY="")
def test_missing_provider_configuration_returns_clean_error(api_key_client):
    response = api_key_client.post(
        reverse("generate"),
        {"prompt": "Hello"},
        format="json",
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "error": {
            "code": "provider_not_configured",
            "message": "The generation provider is not configured.",
        }
    }
