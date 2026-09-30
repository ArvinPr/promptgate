from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json

from django.conf import settings
import redis


class CacheServiceError(Exception):
    """Raised when the optional response cache cannot be read or written."""


@dataclass(frozen=True)
class CachedGeneration:
    output: str
    provider: str
    model: str


class RedisResponseCache:
    key_prefix = "promptgate:response-cache"

    def __init__(self, *, client=None, enabled=None, ttl_seconds=None):
        self.enabled = settings.CACHE_ENABLED if enabled is None else enabled
        self.ttl_seconds = (
            settings.CACHE_TTL_SECONDS if ttl_seconds is None else ttl_seconds
        )
        if self.enabled and self.ttl_seconds <= 0:
            raise CacheServiceError("Response cache configuration is invalid.")

        if not self.enabled:
            self.client = None
        elif client is not None:
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
                raise CacheServiceError("Response cache is unavailable.") from exc

    def get(self, api_key_id, provider: str, model: str, prompt: str):
        if not self.enabled:
            return None

        cache_key = self.build_key(api_key_id, provider, model, prompt)
        try:
            value = self.client.get(cache_key)
            if value is None:
                return None
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            payload = json.loads(value)
            if not isinstance(payload, dict) or not all(
                isinstance(payload.get(field), str)
                for field in ("output", "provider", "model")
            ):
                raise ValueError("Invalid cached generation payload.")
        except (
            redis.RedisError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as exc:
            raise CacheServiceError("Response cache is unavailable.") from exc

        return CachedGeneration(
            output=payload["output"],
            provider=payload["provider"],
            model=payload["model"],
        )

    def set(
        self,
        api_key_id,
        provider: str,
        model: str,
        prompt: str,
        value: CachedGeneration,
    ) -> None:
        if not self.enabled:
            return

        cache_key = self.build_key(api_key_id, provider, model, prompt)
        payload = json.dumps(
            {
                "output": value.output,
                "provider": value.provider,
                "model": value.model,
            },
            separators=(",", ":"),
        )
        try:
            self.client.setex(cache_key, self.ttl_seconds, payload)
        except redis.RedisError as exc:
            raise CacheServiceError("Response cache is unavailable.") from exc

    def build_key(self, api_key_id, provider: str, model: str, prompt: str) -> str:
        prompt_hash = hashlib.sha256(
            prompt.encode("utf-8", errors="surrogatepass")
        ).hexdigest()
        return f"{self.key_prefix}:{api_key_id}:{provider}:{model}:{prompt_hash}"


@lru_cache(maxsize=1)
def get_response_cache() -> RedisResponseCache:
    return RedisResponseCache()
