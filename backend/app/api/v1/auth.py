"""Auth-эндпоинты: OTP-запрос/проверка, обновление токенов (backend.md §5).

Хендлеры тонкие: rate limit/OTP — в core/security, работа с клиентом — в domain/users.
"""

from fastapi import APIRouter, Request

from app.api.v1.deps import RedisDep, SessionDep, SmsDep
from app.api.v1.errors import otp_invalid, otp_rate_limited, token_invalid
from app.api.v1.schemas import OkResponse, OtpRequestIn, OtpVerifyIn, RefreshIn, TokenPair
from app.core.i18n import t
from app.core.security import (
    OtpRateLimitError,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    request_code,
    verify_code,
)
from app.domain.users import service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/otp/request", response_model=OkResponse)
async def otp_request(
    payload: OtpRequestIn, request: Request, redis: RedisDep, sms: SmsDep
) -> OkResponse:
    ip = request.client.host if request.client else "unknown"
    try:
        code = await request_code(redis, payload.phone, ip)
    except OtpRateLimitError as exc:
        raise otp_rate_limited() from exc
    await sms.send(payload.phone, t("otp_code", "ru", code=code))
    return OkResponse()


@router.post("/otp/verify", response_model=TokenPair)
async def otp_verify(payload: OtpVerifyIn, redis: RedisDep, session: SessionDep) -> TokenPair:
    if not await verify_code(redis, payload.phone, payload.code):
        raise otp_invalid()
    user, _ = await service.get_or_create(session, payload.phone)
    await session.commit()
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshIn) -> TokenPair:
    try:
        user_id = decode_token(payload.refresh_token, "refresh")
    except TokenError as exc:
        raise token_invalid() from exc
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )
