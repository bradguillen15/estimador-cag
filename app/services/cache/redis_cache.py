"""Redis-backed exact response cache. The only module that talks to ``redis`` for responses."""

import json

import redis
import structlog

from app.services.cache.base import CachedAnswer

logger = structlog.get_logger()


class RedisResponseCache:
    def __init__(self, client: redis.Redis, ttl: int) -> None:
        self._client = client
        self._ttl = ttl

    @classmethod
    def from_url(cls, url: str, ttl: int) -> "RedisResponseCache":
        # Short timeouts: an unreachable Redis must cost milliseconds, not stall the request.
        client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
        return cls(client, ttl)

    def get(self, key: str) -> CachedAnswer | None:
        try:
            raw = self._client.get(key)
            if raw is None:
                logger.info("cache_miss", key_prefix=key[:32])
                return None
            data = json.loads(raw)
            answer = CachedAnswer(text=data["text"], model=data.get("model"))
        except Exception as exc:
            logger.warning("cache_get_failed", error_type=type(exc).__name__)
            return None
        logger.info("cache_hit", key_prefix=key[:32])
        return answer

    def set(self, key: str, answer: CachedAnswer) -> None:
        try:
            self._client.setex(key, self._ttl, json.dumps({"text": answer.text, "model": answer.model}))
            logger.info("cache_stored", key_prefix=key[:32], ttl=self._ttl)
        except Exception as exc:
            logger.warning("cache_set_failed", error_type=type(exc).__name__)
