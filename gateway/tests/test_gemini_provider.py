from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import override_settings

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
    )

    result = GeminiProvider().generate("Reply briefly")

    assert result.output == "PromptGate OK"
    assert result.provider == "gemini"
    assert result.model == "gemini-test"
    assert result.request_id == "gemini-request-123"
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
