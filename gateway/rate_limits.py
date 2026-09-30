from dataclasses import dataclass
from functools import lru_cache
import time

from django.conf import settings
import redis


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int):
        super().__init__("Rate limit exceeded.")
        self.retry_after_seconds = retry_after_seconds


class RateLimitServiceError(Exception):
    """Raised when request rate limiting cannot be enforced."""


@dataclass(frozen=True)
class RateLimitStatus:
    limit: int
    remaining: int
    retry_after_seconds: int


class RedisRateLimiter:
    _INCREMENT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""

    def __init__(
        self,
        *,
        client=None,
        requests=None,
        window_seconds=None,
        clock=None,
    ):
        self.limit = settings.RATE_LIMIT_REQUESTS if requests is None else requests
        self.window_seconds = (
            settings.RATE_LIMIT_WINDOW_SECONDS
            if window_seconds is None
            else window_seconds
        )
        if self.limit <= 0 or self.window_seconds <= 0:
            raise RateLimitServiceError("Rate limit configuration is invalid.")

        if client is not None:
            self.client = client
        else:
            try:
                self.client = redis.Redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
            except (redis.RedisError, ValueError) as exc:
                raise RateLimitServiceError(
                    "Rate limiting service is unavailable."
                ) from exc
        self.clock = time.time if clock is None else clock

    def check(self, api_key_id) -> RateLimitStatus:
        now = int(self.clock())
        window_start = now - (now % self.window_seconds)
        retry_after_seconds = self.window_seconds - (now % self.window_seconds)
        redis_key = f"promptgate:rate-limit:{api_key_id}:{window_start}"

        try:
            count = int(
                self.client.eval(
                    self._INCREMENT_SCRIPT,
                    1,
                    redis_key,
                    self.window_seconds + 1,
                )
            )
        except (redis.RedisError, TypeError, ValueError) as exc:
            raise RateLimitServiceError(
                "Rate limiting service is unavailable."
            ) from exc

        if count > self.limit:
            raise RateLimitExceeded(retry_after_seconds)

        return RateLimitStatus(
            limit=self.limit,
            remaining=max(0, self.limit - count),
            retry_after_seconds=retry_after_seconds,
        )


@lru_cache(maxsize=1)
def get_rate_limiter() -> RedisRateLimiter:
    return RedisRateLimiter()
