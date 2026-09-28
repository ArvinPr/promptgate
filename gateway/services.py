from gateway.providers.base import GenerationResult, LLMProvider
from gateway.providers.gemini import GeminiProvider


def get_provider() -> LLMProvider:
    return GeminiProvider()


def generate(prompt: str) -> GenerationResult:
    return get_provider().generate(prompt)
