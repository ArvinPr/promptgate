import re
import uuid

import httpx
from django.conf import settings
from google import genai
from google.genai import errors, types

from gateway.providers.base import GenerationResult, LLMProvider, TokenUsage
from gateway.providers.exceptions import (
    ProviderConfigurationError,
    ProviderRequestError,
    ProviderResponseError,
)


class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self, api_key=None, model=None, timeout_ms=None):
        self.api_key = settings.GEMINI_API_KEY if api_key is None else api_key
        self.model = settings.GEMINI_MODEL if model is None else model
        self.timeout_ms = (
            settings.GEMINI_TIMEOUT_MS if timeout_ms is None else timeout_ms
        )

    def generate(self, prompt: str) -> GenerationResult:
        if not self.api_key or not self.model:
            raise ProviderConfigurationError(
                "Gemini provider configuration is incomplete."
            )

        try:
            with genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=self.timeout_ms),
            ) as client:
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                output = response.text
                request_id = getattr(response, "response_id", None) or uuid.uuid4().hex
                usage_metadata = getattr(response, "usage_metadata", None)
        except Exception as exc:
            raise self._map_exception(exc) from exc

        if not isinstance(output, str) or not output.strip():
            raise ProviderResponseError("Gemini returned an empty response.")

        return GenerationResult(
            output=output,
            provider=self.provider_name,
            model=self.model,
            request_id=request_id,
            usage=TokenUsage(
                input_tokens=self._safe_token_count(
                    getattr(usage_metadata, "prompt_token_count", None)
                ),
                output_tokens=self._safe_token_count(
                    getattr(usage_metadata, "candidates_token_count", None)
                ),
                total_tokens=self._safe_token_count(
                    getattr(usage_metadata, "total_token_count", None)
                ),
            ),
        )

    @staticmethod
    def _safe_token_count(value):
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
        return None

    @staticmethod
    def _map_exception(exc: Exception) -> ProviderRequestError:
        category = "request"
        http_status_code = None
        provider_error_code = None
        provider_error_type = None

        if isinstance(exc, errors.APIError):
            http_status_code = GeminiProvider._safe_http_status_code(exc.code)
            provider_error_code = GeminiProvider._safe_provider_error_code(exc.status)
            provider_error_type = type(exc).__name__
            category = GeminiProvider._category_for_api_error(
                http_status_code,
                provider_error_code,
            )
        elif isinstance(exc, httpx.TimeoutException):
            category = "timeout"
            provider_error_type = type(exc).__name__
        elif isinstance(exc, httpx.RequestError):
            category = "network"
            provider_error_type = type(exc).__name__

        return ProviderRequestError(
            "Gemini generation failed.",
            category=category,
            http_status_code=http_status_code,
            provider_error_code=provider_error_code,
            provider_error_type=provider_error_type,
        )

    @staticmethod
    def _safe_http_status_code(value):
        if isinstance(value, int) and 100 <= value <= 599:
            return value
        return None

    @staticmethod
    def _safe_provider_error_code(value):
        if isinstance(value, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", value):
            return value
        return None

    @staticmethod
    def _category_for_api_error(http_status_code, provider_error_code):
        categories_by_status = {
            401: "authentication",
            403: "permission",
            404: "not_found",
            408: "timeout",
            429: "rate_limit",
            504: "timeout",
        }
        if http_status_code in categories_by_status:
            return categories_by_status[http_status_code]
        if http_status_code is not None and 500 <= http_status_code <= 599:
            return "provider_unavailable"

        categories_by_provider_code = {
            "UNAUTHENTICATED": "authentication",
            "PERMISSION_DENIED": "permission",
            "NOT_FOUND": "not_found",
            "RESOURCE_EXHAUSTED": "rate_limit",
            "DEADLINE_EXCEEDED": "timeout",
            "INTERNAL": "provider_unavailable",
            "UNAVAILABLE": "provider_unavailable",
        }
        return categories_by_provider_code.get(provider_error_code, "request")
