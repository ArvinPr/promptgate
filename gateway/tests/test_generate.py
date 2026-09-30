from unittest.mock import Mock, patch

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from gateway.models import GenerationUsage
from gateway.providers.base import GenerationResult, TokenUsage
from gateway.providers.exceptions import ProviderRequestError
from gateway.rate_limits import RateLimitExceeded, RateLimitServiceError


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
def test_generate_rejects_revoked_api_key(
    api_key_client,
    gateway_credentials,
    rate_limiter,
):
    _, api_key, _ = gateway_credentials
    api_key.revoke()

    response = api_key_client.post(
        reverse("generate"),
        {"prompt": "Hello"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "API key has been revoked."}
    rate_limiter.check.assert_not_called()


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
def test_generate_validates_prompt(
    api_key_client,
    rate_limiter,
    payload,
    expected_message,
):
    with patch("gateway.services.get_provider") as get_provider:
        response = api_key_client.post(reverse("generate"), payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert expected_message in response.json()["prompt"][0]
    get_provider.assert_not_called()
    rate_limiter.check.assert_not_called()


@pytest.mark.django_db
def test_generate_records_usage_and_returns_normalized_response(
    api_key_client,
    gateway_credentials,
    rate_limiter,
):
    _, api_key, _ = gateway_credentials
    provider = Mock()
    provider.generate.return_value = GenerationResult(
        output="Database indexes are lookup shortcuts.",
        provider="gemini",
        model="gemini-test",
        request_id="provider-request-123",
        usage=TokenUsage(
            input_tokens=8,
            output_tokens=5,
            total_tokens=13,
        ),
    )

    with (
        patch("gateway.services.get_provider", return_value=provider),
        patch(
            "gateway.services.time.perf_counter_ns",
            side_effect=[1_000_000_000, 1_012_000_000],
        ),
    ):
        response = api_key_client.post(
            reverse("generate"),
            {"prompt": "Explain database indexes."},
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data == {
        "output": "Database indexes are lookup shortcuts.",
        "provider": "gemini",
        "model": "gemini-test",
        "request_id": response_data["request_id"],
        "usage": {
            "input_tokens": 8,
            "output_tokens": 5,
            "total_tokens": 13,
        },
        "latency_ms": 12,
    }
    provider.generate.assert_called_once_with("Explain database indexes.")
    rate_limiter.check.assert_called_once_with(api_key.pk)

    usage = GenerationUsage.objects.get()
    assert usage.request_id == response_data["request_id"]
    assert usage.api_key == api_key
    assert usage.provider == "gemini"
    assert usage.model == "gemini-test"
    assert usage.input_tokens == 8
    assert usage.output_tokens == 5
    assert usage.total_tokens == 13
    assert usage.latency_ms == 12
    assert usage.status == GenerationUsage.Status.SUCCEEDED
    assert usage.error_category == ""


@pytest.mark.django_db
def test_usage_model_does_not_store_prompt_or_output():
    field_names = {field.name for field in GenerationUsage._meta.get_fields()}

    assert "prompt" not in field_names
    assert "output" not in field_names


@pytest.mark.django_db
def test_generate_assigns_a_unique_request_id_to_every_provider_call(
    api_key_client,
):
    provider = Mock()
    provider.generate.return_value = GenerationResult(
        output="Generated text",
        provider="gemini",
        model="gemini-test",
        request_id="same-provider-request-id",
    )

    with patch("gateway.services.get_provider", return_value=provider):
        first_response = api_key_client.post(
            reverse("generate"),
            {"prompt": "First"},
            format="json",
        )
        second_response = api_key_client.post(
            reverse("generate"),
            {"prompt": "Second"},
            format="json",
        )

    first_request_id = first_response.json()["request_id"]
    second_request_id = second_response.json()["request_id"]
    assert first_request_id != second_request_id
    assert set(GenerationUsage.objects.values_list("request_id", flat=True)) == {
        first_request_id,
        second_request_id,
    }


@pytest.mark.django_db
def test_provider_failure_is_recorded_with_safe_metadata(
    api_key_client,
    gateway_credentials,
):
    _, api_key, _ = gateway_credentials
    provider = Mock()
    provider.provider_name = "gemini"
    provider.model = "gemini-test"
    provider.generate.side_effect = ProviderRequestError(
        "Internal SDK failure containing sensitive details",
        category="provider_unavailable",
    )

    with (
        patch("gateway.services.get_provider", return_value=provider),
        patch(
            "gateway.services.time.perf_counter_ns",
            side_effect=[2_000_000_000, 2_025_000_000],
        ),
    ):
        response = api_key_client.post(
            reverse("generate"),
            {"prompt": "Hello"},
            format="json",
        )

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    response_data = response.json()
    assert response_data == {
        "error": {
            "code": "provider_error",
            "message": "The generation provider is temporarily unavailable.",
        },
        "request_id": response_data["request_id"],
    }
    assert "sensitive" not in response.content.decode().lower()

    usage = GenerationUsage.objects.get()
    assert usage.request_id == response_data["request_id"]
    assert usage.api_key == api_key
    assert usage.provider == "gemini"
    assert usage.model == "gemini-test"
    assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.total_tokens is None
    assert usage.latency_ms == 25
    assert usage.status == GenerationUsage.Status.FAILED
    assert usage.error_category == "provider_unavailable"
    assert "sensitive" not in str(usage.__dict__).lower()


@pytest.mark.django_db
@override_settings(GEMINI_API_KEY="")
def test_missing_provider_configuration_returns_clean_error(api_key_client):
    response = api_key_client.post(
        reverse("generate"),
        {"prompt": "Hello"},
        format="json",
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    response_data = response.json()
    assert response_data == {
        "error": {
            "code": "provider_not_configured",
            "message": "The generation provider is not configured.",
        },
        "request_id": response_data["request_id"],
    }


@pytest.mark.django_db
def test_rate_limit_allows_request_below_threshold(api_key_client, rate_limiter):
    provider = Mock()
    provider.generate.return_value = GenerationResult(
        output="Allowed",
        provider="gemini",
        model="gemini-test",
        request_id="provider-request-id",
    )

    with patch("gateway.services.get_provider", return_value=provider):
        response = api_key_client.post(
            reverse("generate"),
            {"prompt": "Hello"},
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK
    rate_limiter.check.assert_called_once()
    provider.generate.assert_called_once_with("Hello")


@pytest.mark.django_db
def test_rate_limit_blocks_request_without_calling_provider(
    api_key_client,
    rate_limiter,
):
    rate_limiter.check.side_effect = RateLimitExceeded(17)

    with patch("gateway.services.get_provider") as get_provider:
        response = api_key_client.post(
            reverse("generate"),
            {"prompt": "Hello"},
            format="json",
        )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json() == {
        "error": {
            "code": "rate_limit_exceeded",
            "message": "Rate limit exceeded.",
            "retry_after_seconds": 17,
        }
    }
    assert response.headers["Retry-After"] == "17"
    get_provider.assert_not_called()
    assert not GenerationUsage.objects.exists()


@pytest.mark.django_db
def test_redis_failure_returns_controlled_error_without_calling_provider(
    api_key_client,
    rate_limiter,
):
    rate_limiter.check.side_effect = RateLimitServiceError(
        "Raw Redis details must not escape"
    )

    with patch("gateway.services.get_provider") as get_provider:
        response = api_key_client.post(
            reverse("generate"),
            {"prompt": "Hello"},
            format="json",
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "error": {
            "code": "rate_limit_unavailable",
            "message": "Rate limiting service is temporarily unavailable.",
        }
    }
    assert "raw redis" not in response.content.decode().lower()
    get_provider.assert_not_called()
    assert not GenerationUsage.objects.exists()
