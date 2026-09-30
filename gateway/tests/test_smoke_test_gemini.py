from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import override_settings

from gateway.providers.base import GenerationResult
from gateway.providers.exceptions import ProviderRequestError


@override_settings(GEMINI_MODEL="gemini-test")
@patch("gateway.management.commands.smoke_test_gemini.GeminiProvider.generate")
def test_smoke_command_reports_success(generate):
    generate.return_value = GenerationResult(
        output="PromptGate OK",
        provider="gemini",
        model="gemini-test",
        request_id="request-123",
    )
    stdout = StringIO()

    call_command("smoke_test_gemini", "Reply exactly", stdout=stdout)

    assert stdout.getvalue().splitlines() == [
        "success: true",
        "model: gemini-test",
        "returned_text: PromptGate OK",
    ]


@override_settings(GEMINI_MODEL="gemini-test")
@patch("gateway.management.commands.smoke_test_gemini.GeminiProvider.generate")
def test_smoke_command_reports_only_sanitized_failure_diagnostics(generate):
    generate.side_effect = ProviderRequestError(
        "raw x-goog-api-key: secret-value",
        category="not_found",
        http_status_code=404,
        provider_error_code="NOT_FOUND",
        provider_error_type="ClientError",
    )
    stdout = StringIO()

    call_command("smoke_test_gemini", "Reply exactly", stdout=stdout)

    output = stdout.getvalue()
    assert output.splitlines() == [
        "success: false",
        "model: gemini-test",
        "sanitized_category: not_found",
        "http_status_code: 404",
        "provider_error_code: NOT_FOUND",
        "provider_error_type: ClientError",
    ]
    assert "secret-value" not in output
    assert "x-goog-api-key" not in output
