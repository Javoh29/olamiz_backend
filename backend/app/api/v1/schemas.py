"""Pydantic-схемы API v1 (контракты запросов/ответов)."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.users.models import UserLanguage

# Узбекский номер в E.164: +998 и 9 цифр.
PHONE_PATTERN = r"^\+998\d{9}$"


class OtpRequestIn(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)


class OtpVerifyIn(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    code: str = Field(pattern=r"^\d{6}$")
    # Акцепт оферты обязателен только при регистрации нового клиента;
    # offer_version — версия, которую клиент показал пользователю (фиксируется в acceptance).
    offer_accepted: bool = False
    offer_version: str | None = None


class OfferOut(BaseModel):
    version: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class OkResponse(BaseModel):
    ok: bool = True


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    name: str | None
    language: UserLanguage
    client_rating: Decimal | None
    deals_count: int


class MePatchIn(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    language: UserLanguage | None = None
