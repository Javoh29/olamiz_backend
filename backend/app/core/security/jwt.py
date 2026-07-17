"""JWT access/refresh (HS256 на JWT_SECRET)."""

from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    """Некорректный/просроченный токен или неверный тип."""


def _create(user_id: int, token_type: TokenType, ttl: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _create(user_id, "access", timedelta(minutes=get_settings().jwt_access_ttl_min))


def create_refresh_token(user_id: int) -> str:
    return _create(user_id, "refresh", timedelta(days=get_settings().jwt_refresh_ttl_days))


def decode_token(token: str, expected_type: TokenType = "access") -> int:
    """Вернуть user_id из валидного токена нужного типа, иначе TokenError."""
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenError("invalid token") from exc
    if payload.get("type") != expected_type:
        raise TokenError("wrong token type")
    try:
        return int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise TokenError("invalid subject") from exc
