from unittest.mock import patch

import pytest
import redis

from gateway.rate_limits import (
    RateLimitExceeded,
    RateLimitServiceError,
    RedisRateLimiter,
)


class FakeRedis:
    def __init__(self):
        self.counts = {}

    def eval(self, script, key_count, key, ttl):
        assert "INCR" in script
        assert key_count == 1
        assert ttl == 61
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]


def test_fixed_window_allows_requests_below_the_limit_and_then_blocks():
    limiter = RedisRateLimiter(
        client=FakeRedis(),
        requests=2,
        window_seconds=60,
        clock=lambda: 125,
    )

    first = limiter.check("api-key-1")
    second = limiter.check("api-key-1")

    assert first.remaining == 1
    assert second.remaining == 0
    with pytest.raises(RateLimitExceeded) as caught:
        limiter.check("api-key-1")
    assert caught.value.retry_after_seconds == 55


def test_fixed_window_maintains_independent_api_key_limits():
    limiter = RedisRateLimiter(
        client=FakeRedis(),
        requests=1,
        window_seconds=60,
        clock=lambda: 125,
    )

    limiter.check("api-key-1")
    with pytest.raises(RateLimitExceeded):
        limiter.check("api-key-1")

    other_key = limiter.check("api-key-2")

    assert other_key.remaining == 0


def test_redis_errors_are_converted_to_controlled_service_errors():
    class UnavailableRedis:
        def eval(self, *args):
            raise redis.ConnectionError("Internal connection details")

    limiter = RedisRateLimiter(
        client=UnavailableRedis(),
        requests=1,
        window_seconds=60,
        clock=lambda: 125,
    )

    with pytest.raises(RateLimitServiceError) as caught:
        limiter.check("api-key-1")

    assert str(caught.value) == "Rate limiting service is unavailable."
    assert "Internal connection details" not in str(caught.value)


def test_invalid_redis_configuration_is_a_controlled_service_error():
    with patch(
        "gateway.rate_limits.redis.Redis.from_url",
        side_effect=ValueError("Raw Redis URL details"),
    ):
        with pytest.raises(RateLimitServiceError) as caught:
            RedisRateLimiter(requests=1, window_seconds=60)

    assert str(caught.value) == "Rate limiting service is unavailable."
    assert "Raw Redis URL details" not in str(caught.value)
