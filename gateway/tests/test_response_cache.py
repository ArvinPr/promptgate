import uuid

import pytest

from gateway.response_cache import (
    CachedGeneration,
    CacheServiceError,
    RedisResponseCache,
)


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.last_key = None
        self.last_ttl = None

    def get(self, key):
        self.last_key = key
        return self.values.get(key)

    def setex(self, key, ttl, value):
        self.last_key = key
        self.last_ttl = ttl
        self.values[key] = value


def test_cache_key_excludes_raw_prompt_and_raw_api_key():
    redis_client = FakeRedis()
    cache = RedisResponseCache(
        client=redis_client,
        enabled=True,
        ttl_seconds=300,
    )
    api_key_id = uuid.uuid4()
    raw_api_key = "pg_raw-client-secret"
    prompt = "A private prompt that must not enter the key"

    cache.set(
        api_key_id,
        "gemini",
        "gemini-test",
        prompt,
        CachedGeneration(
            output="Cached output",
            provider="gemini",
            model="gemini-test",
        ),
    )

    assert str(api_key_id) in redis_client.last_key
    assert prompt not in redis_client.last_key
    assert raw_api_key not in redis_client.last_key
    assert redis_client.last_ttl == 300


def test_cache_entries_are_isolated_by_api_key_id():
    redis_client = FakeRedis()
    cache = RedisResponseCache(
        client=redis_client,
        enabled=True,
        ttl_seconds=300,
    )
    first_api_key_id = uuid.uuid4()
    second_api_key_id = uuid.uuid4()
    cached_generation = CachedGeneration(
        output="First client's output",
        provider="gemini",
        model="gemini-test",
    )
    cache.set(
        first_api_key_id,
        "gemini",
        "gemini-test",
        "Same prompt",
        cached_generation,
    )

    assert (
        cache.get(
            second_api_key_id,
            "gemini",
            "gemini-test",
            "Same prompt",
        )
        is None
    )
    assert (
        cache.get(
            first_api_key_id,
            "gemini",
            "gemini-test",
            "Same prompt",
        )
        == cached_generation
    )


def test_invalid_cached_payload_is_a_controlled_cache_failure():
    redis_client = FakeRedis()
    cache = RedisResponseCache(
        client=redis_client,
        enabled=True,
        ttl_seconds=300,
    )
    api_key_id = uuid.uuid4()
    cache_key = cache.build_key(
        api_key_id,
        "gemini",
        "gemini-test",
        "Prompt",
    )
    redis_client.values[cache_key] = "[]"

    with pytest.raises(CacheServiceError, match="Response cache is unavailable"):
        cache.get(api_key_id, "gemini", "gemini-test", "Prompt")
