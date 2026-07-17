"""Async Redis-клиент (ARQ, OTP, rate-limit, кэш)."""

from redis.asyncio import Redis

from app.core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    """Ленивый singleton-клиент. decode_responses — работаем со строками, не байтами."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis
