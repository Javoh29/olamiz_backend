"""Интеграционные тесты auth-флоу: OTP → JWT → /me, ошибки в едином формате."""

import fakeredis.aioredis
from httpx import AsyncClient

PHONE = "+998901112233"


async def _current_offer(client: AsyncClient) -> str:
    resp = await client.get("/api/v1/auth/offer")
    assert resp.status_code == 200
    version: str = resp.json()["version"]
    return version


async def _login(client: AsyncClient, redis: fakeredis.aioredis.FakeRedis) -> dict[str, str]:
    await client.post("/api/v1/auth/otp/request", json={"phone": PHONE})
    code = await redis.get(f"otp:code:{PHONE}")
    version = await _current_offer(client)
    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "code": code, "offer_accepted": True, "offer_version": version},
    )
    assert resp.status_code == 200
    return resp.json()


async def test_offer_endpoint(client: AsyncClient) -> None:
    from app.core.config import get_settings

    assert await _current_offer(client) == get_settings().offer_version


async def test_full_flow(client: AsyncClient, redis: fakeredis.aioredis.FakeRedis) -> None:
    resp = await client.post("/api/v1/auth/otp/request", json={"phone": PHONE})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    code = await redis.get(f"otp:code:{PHONE}")
    assert code is not None
    version = await _current_offer(client)

    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "code": code, "offer_accepted": True, "offer_version": version},
    )
    assert resp.status_code == 200
    access = resp.json()["access_token"]

    resp = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["phone"] == PHONE
    assert body["language"] == "ru"
    assert body["deals_count"] == 0


async def test_register_requires_offer(
    client: AsyncClient, redis: fakeredis.aioredis.FakeRedis
) -> None:
    await client.post("/api/v1/auth/otp/request", json={"phone": PHONE})
    code = await redis.get(f"otp:code:{PHONE}")
    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "code": code, "offer_accepted": False},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "offer_required"
    # код не израсходован — с принятой офертой тот же код проходит
    version = await _current_offer(client)
    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "code": code, "offer_accepted": True, "offer_version": version},
    )
    assert resp.status_code == 200


async def test_register_offer_version_outdated(
    client: AsyncClient, redis: fakeredis.aioredis.FakeRedis
) -> None:
    await client.post("/api/v1/auth/otp/request", json={"phone": PHONE})
    code = await redis.get(f"otp:code:{PHONE}")
    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "code": code, "offer_accepted": True, "offer_version": "1999-01"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "offer_outdated"


async def test_existing_user_logs_in_without_offer(
    client: AsyncClient, redis: fakeredis.aioredis.FakeRedis
) -> None:
    await _login(client, redis)  # регистрация с офертой
    # повторный вход того же клиента — оферта уже принята, флаг не нужен
    await client.post("/api/v1/auth/otp/request", json={"phone": PHONE})
    code = await redis.get(f"otp:code:{PHONE}")
    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "code": code, "offer_accepted": False},
    )
    assert resp.status_code == 200


async def test_verify_invalid_code_error_format(
    client: AsyncClient, redis: fakeredis.aioredis.FakeRedis
) -> None:
    await client.post("/api/v1/auth/otp/request", json={"phone": PHONE})
    version = await _current_offer(client)
    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "code": "000000", "offer_accepted": True, "offer_version": version},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "otp_invalid"
    assert "message_ru" in body and "message_uz" in body


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthorized"


async def test_refresh_issues_new_pair(
    client: AsyncClient, redis: fakeredis.aioredis.FakeRedis
) -> None:
    tokens = await _login(client, redis)
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_patch_me(client: AsyncClient, redis: fakeredis.aioredis.FakeRedis) -> None:
    tokens = await _login(client, redis)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    resp = await client.patch("/api/v1/me", json={"name": "Али", "language": "uz"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Али"
    assert body["language"] == "uz"


async def test_invalid_phone_rejected(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/otp/request", json={"phone": "12345"})
    assert resp.status_code == 422  # pydantic-валидация формата
