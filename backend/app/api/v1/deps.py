"""Зависимости API v1: сессия, Redis, SMS-шлюз, текущий пользователь."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import token_invalid, unauthorized
from app.core.db import get_session
from app.core.redis import get_redis
from app.core.security import TokenError, decode_token
from app.core.sms import LogSmsGateway, SmsGateway
from app.domain.users import service
from app.domain.users.models import User

_bearer = HTTPBearer(auto_error=False)


def get_sms() -> SmsGateway:
    return LogSmsGateway()


SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]
SmsDep = Annotated[SmsGateway, Depends(get_sms)]


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        user_id = decode_token(credentials.credentials, "access")
    except TokenError as exc:
        raise token_invalid() from exc
    user = await service.get_by_id(session, user_id)
    if user is None:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
