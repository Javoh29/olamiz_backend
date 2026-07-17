"""OTP: генерация/проверка, TTL, rate limit, защита от перебора (backend.md §10.6)."""

import fakeredis.aioredis
import pytest

from app.core.config import get_settings
from app.core.security.otp import OtpRateLimitError, request_code, verify_code

PHONE = "+998901234567"
IP = "127.0.0.1"


async def test_request_and_verify_success(redis: fakeredis.aioredis.FakeRedis) -> None:
    code = await request_code(redis, PHONE, IP)
    assert len(code) == 6 and code.isdigit()
    assert await verify_code(redis, PHONE, code) is True
    # код одноразовый — повторная проверка не проходит
    assert await verify_code(redis, PHONE, code) is False


async def test_verify_wrong_code(redis: fakeredis.aioredis.FakeRedis) -> None:
    await request_code(redis, PHONE, IP)
    assert await verify_code(redis, PHONE, "000000") is False


async def test_verify_without_request(redis: fakeredis.aioredis.FakeRedis) -> None:
    assert await verify_code(redis, PHONE, "123456") is False


async def test_ttl_is_set(redis: fakeredis.aioredis.FakeRedis) -> None:
    await request_code(redis, PHONE, IP)
    ttl = await redis.ttl(f"otp:code:{PHONE}")
    assert 0 < ttl <= get_settings().otp_ttl_min * 60


async def test_rate_limit_per_phone(redis: fakeredis.aioredis.FakeRedis) -> None:
    limit = get_settings().otp_rate_per_phone_hour
    for _ in range(limit):
        await request_code(redis, PHONE, IP)
    with pytest.raises(OtpRateLimitError):
        await request_code(redis, PHONE, IP)


async def test_verify_attempts_exhausted(redis: fakeredis.aioredis.FakeRedis) -> None:
    code = await request_code(redis, PHONE, IP)
    for _ in range(5):
        assert await verify_code(redis, PHONE, "000000") is False
    # после исчерпания попыток даже верный код не проходит
    assert await verify_code(redis, PHONE, code) is False
