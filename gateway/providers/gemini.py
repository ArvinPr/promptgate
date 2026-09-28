import uuid

from django.conf import settings
from google import genai
from google.genai import types

from gateway.providers.base import GenerationResult, LLMProvider
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
        except Exception as exc:
            raise ProviderRequestError("Gemini generation failed.") from exc

        if not isinstance(output, str) or not output.strip():
            raise ProviderResponseError("Gemini returned an empty response.")

        return GenerationResult(
            output=output,
            provider=self.provider_name,
            model=self.model,
            request_id=request_id,
        )
