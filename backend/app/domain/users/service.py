"""Бизнес-логика клиентов: поиск/создание по телефону, профиль, акцепт оферты."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.users.models import OfferAcceptance, User, UserLanguage


class OfferRequired(Exception):
    """Новый клиент не принял оферту."""


class OfferVersionMismatch(Exception):
    """Клиент прислал версию оферты, отличную от текущей (показывал устаревшую)."""

    def __init__(self, current: str) -> None:
        self.current = current
        super().__init__(current)


def validate_offer_for_registration(offer_accepted: bool, offer_version: str | None) -> None:
    """Проверить акцепт оферты для регистрации нового клиента (D15).

    Вызывается ДО проверки OTP-кода, чтобы не расходовать код при непринятой оферте.
    """
    current = get_settings().offer_version
    if not offer_accepted:
        raise OfferRequired
    if offer_version != current:
        raise OfferVersionMismatch(current)


async def get_by_phone(session: AsyncSession, phone: str) -> User | None:
    return (await session.scalars(select(User).where(User.phone == phone))).first()


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_or_create(session: AsyncSession, phone: str) -> tuple[User, bool]:
    """Вернуть клиента по телефону; при первом входе создать и зафиксировать акцепт оферты.

    Фиксируется текущая версия оферты (валидация версии — в validate_offer_for_registration).
    """
    user = await get_by_phone(session, phone)
    if user is not None:
        return user, False
    user = User(phone=phone)
    session.add(user)
    await session.flush()
    session.add(OfferAcceptance(user_id=user.id, offer_version=get_settings().offer_version))
    return user, True


async def update_profile(
    session: AsyncSession,
    user: User,
    *,
    name: str | None = None,
    language: UserLanguage | None = None,
) -> User:
    """Обновить профиль. Переданные (не None) поля применяются; очистка имени не предусмотрена."""
    if name is not None:
        user.name = name
    if language is not None:
        user.language = language
    await session.flush()
    return user
