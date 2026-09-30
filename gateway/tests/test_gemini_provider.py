from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from django.test import override_settings
from google.genai import errors

from gateway.providers.exceptions import ProviderRequestError
from gateway.providers.gemini import GeminiProvider


@override_settings(
    GEMINI_API_KEY="test-api-key",
    GEMINI_MODEL="gemini-test",
    GEMINI_TIMEOUT_MS=30_000,
)
@patch("gateway.providers.gemini.genai.Client")
def test_gemini_provider_calls_sdk_and_normalizes_response(client_class):
    client = client_class.return_value.__enter__.return_value
    client.models.generate_content.return_value = SimpleNamespace(
        text="PromptGate OK",
        response_id="gemini-request-123",
        usage_metadata=SimpleNamespace(
            prompt_token_count=7,
            candidates_token_count=3,
            total_token_count=10,
        ),
    )

    result = GeminiProvider().generate("Reply briefly")

    assert result.output == "PromptGate OK"
    assert result.provider == "gemini"
    assert result.model == "gemini-test"
    assert result.request_id == "gemini-request-123"
    assert result.usage.input_tokens == 7
    assert result.usage.output_tokens == 3
    assert result.usage.total_tokens == 10
    client.models.generate_content.assert_called_once_with(
        model="gemini-test",
        contents="Reply briefly",
    )
    assert client_class.call_args.kwargs["api_key"] == "test-api-key"
    assert client_class.call_args.kwargs["http_options"].timeout == 30_000


@override_settings(
    GEMINI_API_KEY="test-api-key",
    GEMINI_MODEL="gemini-test",
)
@patch("gateway.providers.gemini.genai.Client")
def test_gemini_provider_translates_sdk_errors(client_class):
    client = client_class.return_value.__enter__.return_value
    client.models.generate_content.side_effect = RuntimeError(
        "SDK details must not escape"
    )

    with pytest.raises(ProviderRequestError, match="Gemini generation failed") as exc:
        GeminiProvider().generate("Hello")

    assert "SDK details" not in str(exc.value)
    assert exc.value.category == "request"
    assert exc.value.http_status_code is None
    assert exc.value.provider_error_code is None
    assert exc.value.provider_error_type is None


@pytest.mark.parametrize(
    ("error_class", "status_code", "provider_code", "expected_category"),
    [
        (errors.ClientError, 401, "UNAUTHENTICATED", "authentication"),
        (errors.ClientError, 403, "PERMISSION_DENIED", "permission"),
        (errors.ClientError, 404, "NOT_FOUND", "not_found"),
        (errors.ClientError, 429, "RESOURCE_EXHAUSTED", "rate_limit"),
        (errors.ServerError, 504, "DEADLINE_EXCEEDED", "timeout"),
        (errors.ServerError, 503, "UNAVAILABLE", "provider_unavailable"),
        (errors.ClientError, 400, "INVALID_ARGUMENT", "request"),
    ],
)
@override_settings(
    GEMINI_API_KEY="test-api-key",
    GEMINI_MODEL="gemini-test",
)
@patch("gateway.providers.gemini.genai.Client")
def test_gemini_provider_classifies_api_errors(
    client_class,
    error_class,
    status_code,
    provider_code,
    expected_category,
):
    client = client_class.return_value.__enter__.return_value
    client.models.generate_content.side_effect = error_class(
        status_code,
        {
            "error": {
                "status": provider_code,
                "message": "Sensitive provider details",
            }
        },
    )

    with pytest.raises(ProviderRequestError) as caught:
        GeminiProvider().generate("Hello")

    error = caught.value
    assert str(error) == "Gemini generation failed."
    assert error.category == expected_category
    assert error.http_status_code == status_code
    assert error.provider_error_code == provider_code
    assert error.provider_error_type == error_class.__name__
    assert "Sensitive provider details" not in str(error)


@pytest.mark.parametrize(
    ("sdk_error", "expected_category", "expected_type"),
    [
        (httpx.ReadTimeout("timed out"), "timeout", "ReadTimeout"),
        (httpx.ConnectError("connection failed"), "network", "ConnectError"),
    ],
)
@override_settings(
    GEMINI_API_KEY="test-api-key",
    GEMINI_MODEL="gemini-test",
)
@patch("gateway.providers.gemini.genai.Client")
def test_gemini_provider_classifies_transport_errors(
    client_class,
    sdk_error,
    expected_category,
    expected_type,
):
    client = client_class.return_value.__enter__.return_value
    client.models.generate_content.side_effect = sdk_error

    with pytest.raises(ProviderRequestError) as caught:
        GeminiProvider().generate("Hello")

    error = caught.value
    assert error.category == expected_category
    assert error.http_status_code is None
    assert error.provider_error_code is None
    assert error.provider_error_type == expected_type
    assert str(sdk_error) not in str(error)


def test_gemini_provider_rejects_unsafe_provider_error_code():
    error = errors.APIError(
        400,
        {"error": {"status": "bad value: secret", "message": "Sensitive details"}},
    )

    mapped = GeminiProvider._map_exception(error)

    assert mapped.category == "request"
    assert mapped.provider_error_code is None
