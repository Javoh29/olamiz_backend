"""Async engine и session factory (SQLAlchemy 2.0)."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей; metadata используется Alembic."""


engine: AsyncEngine = create_async_engine(get_settings().database_url, echo=get_settings().debug)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI-зависимость: одна сессия на запрос."""
    async with session_factory() as session:
        yield session
