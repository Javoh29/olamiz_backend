"""OTP: генерация 6-значного кода, TTL, rate limit, ограничение попыток ввода.

Хранилище — Redis. Ключи:
- otp:code:{phone}      код, TTL = OTP_TTL_MIN
- otp:attempts:{phone}  счётчик неверных вводов (защита от перебора)
- otp:rl:phone:{phone}  лимит запросов на телефон (в час)
- otp:rl:ip:{ip}        лимит запросов на IP (в час)
"""

import secrets

from redis.asyncio import Redis

from app.core.config import get_settings

_MAX_VERIFY_ATTEMPTS = 5
_RATE_WINDOW_SEC = 3600


class OtpRateLimitError(Exception):
    """Превышен лимит запросов OTP (на телефон или IP)."""


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def _hit_rate_limit(redis: Redis, key: str, limit: int) -> None:
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _RATE_WINDOW_SEC)
    if count > limit:
        raise OtpRateLimitError(key)


async def request_code(redis: Redis, phone: str, ip: str) -> str:
    """Проверить лимиты, сгенерировать и сохранить код, вернуть его для отправки."""
    settings = get_settings()
    await _hit_rate_limit(redis, f"otp:rl:phone:{phone}", settings.otp_rate_per_phone_hour)
    await _hit_rate_limit(redis, f"otp:rl:ip:{ip}", settings.otp_rate_per_ip_hour)

    code = _generate_code()
    await redis.set(f"otp:code:{phone}", code, ex=settings.otp_ttl_min * 60)
    await redis.delete(f"otp:attempts:{phone}")
    return code


async def verify_code(redis: Redis, phone: str, code: str) -> bool:
    """Сверить код. При успехе — инвалидировать. Ограничение попыток — от перебора."""
    settings = get_settings()
    stored = await redis.get(f"otp:code:{phone}")
    if stored is None:
        return False

    attempts = await redis.incr(f"otp:attempts:{phone}")
    if attempts == 1:
        await redis.expire(f"otp:attempts:{phone}", settings.otp_ttl_min * 60)
    if attempts > _MAX_VERIFY_ATTEMPTS:
        await redis.delete(f"otp:code:{phone}")
        return False

    if secrets.compare_digest(stored, code):
        await redis.delete(f"otp:code:{phone}", f"otp:attempts:{phone}")
        return True
    return False
