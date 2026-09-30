from dataclasses import replace
import time
import uuid

from accounts.models import APIKey
from gateway.models import GenerationUsage
from gateway.providers.base import GenerationResult, LLMProvider, TokenUsage
from gateway.providers.exceptions import ProviderError
from gateway.providers.gemini import GeminiProvider
from gateway.response_cache import (
    CachedGeneration,
    CacheServiceError,
    get_response_cache,
)


SAFE_ERROR_CATEGORIES = {
    "authentication",
    "configuration",
    "network",
    "not_found",
    "permission",
    "provider",
    "provider_unavailable",
    "rate_limit",
    "request",
    "response",
    "timeout",
}


def get_provider() -> LLMProvider:
    return GeminiProvider()


def generate(prompt: str, api_key: APIKey) -> GenerationResult:
    request_id = uuid.uuid4().hex
    provider = get_provider()
    provider_name = _safe_provider_value(getattr(provider, "provider_name", None))
    model = _safe_provider_value(getattr(provider, "model", None))
    response_cache = _get_response_cache()

    cached_generation = _get_cached_generation(
        response_cache,
        api_key.pk,
        provider_name,
        model,
        prompt,
    )
    if cached_generation is not None:
        result = GenerationResult(
            output=cached_generation.output,
            provider=cached_generation.provider,
            model=cached_generation.model,
            request_id=request_id,
            usage=TokenUsage(
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
            ),
            latency_ms=0,
            cached=True,
        )
        GenerationUsage.objects.create(
            request_id=request_id,
            api_key=api_key,
            provider=result.provider,
            model=result.model,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            latency_ms=0,
            status=GenerationUsage.Status.SUCCEEDED,
            cache_hit=True,
        )
        return result

    started_at = time.perf_counter_ns()

    try:
        provider_result = provider.generate(prompt)
    except ProviderError as exc:
        latency_ms = _elapsed_ms(started_at)
        GenerationUsage.objects.create(
            request_id=request_id,
            api_key=api_key,
            provider=provider_name,
            model=model,
            latency_ms=latency_ms,
            status=GenerationUsage.Status.FAILED,
            error_category=_safe_error_category(exc.category),
        )
        exc.request_id = request_id
        raise

    latency_ms = _elapsed_ms(started_at)
    result = replace(
        provider_result,
        request_id=request_id,
        latency_ms=latency_ms,
        cached=False,
    )
    GenerationUsage.objects.create(
        request_id=request_id,
        api_key=api_key,
        provider=result.provider,
        model=result.model,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        total_tokens=result.usage.total_tokens,
        latency_ms=latency_ms,
        status=GenerationUsage.Status.SUCCEEDED,
    )
    _cache_generation(
        response_cache,
        api_key.pk,
        provider_name,
        model,
        prompt,
        result,
    )
    return result


def _get_response_cache():
    try:
        return get_response_cache()
    except CacheServiceError:
        return None


def _get_cached_generation(cache, api_key_id, provider, model, prompt):
    if cache is None:
        return None
    try:
        return cache.get(api_key_id, provider, model, prompt)
    except CacheServiceError:
        return None


def _cache_generation(cache, api_key_id, provider, model, prompt, result):
    if cache is None:
        return
    try:
        cache.set(
            api_key_id,
            provider,
            model,
            prompt,
            CachedGeneration(
                output=result.output,
                provider=result.provider,
                model=result.model,
            ),
        )
    except CacheServiceError:
        return


def _elapsed_ms(started_at: int) -> int:
    elapsed_ns = max(0, time.perf_counter_ns() - started_at)
    return round(elapsed_ns / 1_000_000)


def _safe_provider_value(value) -> str:
    if isinstance(value, str) and value:
        return value[:100]
    return "unknown"


def _safe_error_category(value) -> str:
    if value in SAFE_ERROR_CATEGORIES:
        return value
    return "provider"
