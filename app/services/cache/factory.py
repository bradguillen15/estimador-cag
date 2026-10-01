"""Builds the response cache from settings."""

from app.config import Settings
from app.services.cache.base import NoOpCache, ResponseCache
from app.services.cache.redis_cache import RedisResponseCache


def get_response_cache(settings: Settings) -> ResponseCache:
    """Redis when ``CACHE_ENABLED``; otherwise a no-op. Never connects at build time."""
    if not settings.cache_enabled:
        return NoOpCache()
    return RedisResponseCache.from_url(settings.redis_url, ttl=settings.cache_ttl)
