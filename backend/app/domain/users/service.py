"""Бизнес-логика клиентов: поиск/создание по телефону, профиль, акцепт оферты."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.users.models import OfferAcceptance, User, UserLanguage


async def get_by_phone(session: AsyncSession, phone: str) -> User | None:
    return (await session.scalars(select(User).where(User.phone == phone))).first()


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_or_create(session: AsyncSession, phone: str) -> tuple[User, bool]:
    """Вернуть клиента по телефону; при первом входе создать и зафиксировать акцепт оферты."""
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
