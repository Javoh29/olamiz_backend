"""Pydantic-схемы API v1 (контракты запросов/ответов)."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.catalog.models import DepositKind
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


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name_ru: str
    name_uz: str
    slug: str
    children: list["CategoryOut"] = []


CategoryOut.model_rebuild()


class ListingItemOut(BaseModel):
    """Карточка в ленте каталога (телефон прокатчика тут не отдаётся никогда)."""

    id: int
    title: str
    price_per_day: int
    deposit_kind: DepositKind
    deposit_amount: int | None
    rating: Decimal | None
    district_id: int
    supplier_name: str
    thumbnail: str | None  # presigned URL первого фото, если есть


class SupplierPublicOut(BaseModel):
    id: int
    display_name: str
    district_id: int
    rating: Decimal | None
    # Телефон — ТОЛЬКО у клиента с подтверждённой бронью этой карточки (backend.md §5);
    # иначе None. Скрытие — на сервере, не на клиенте.
    phone: str | None = None


class ListingDetailOut(BaseModel):
    id: int
    title: str
    description: str | None
    price_per_day: int
    deposit_kind: DepositKind
    deposit_amount: int | None
    quantity: int
    rating: Decimal | None
    fits_photo_pct: Decimal | None
    slug: str
    category_id: int
    photos: list[str]  # presigned URLs
    supplier: SupplierPublicOut
