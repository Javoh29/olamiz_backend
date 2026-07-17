"""Async engine и session factory (SQLAlchemy 2.0)."""

from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings

# Детерминированные имена констрейнтов/индексов — чтобы Alembic-миграции были
# воспроизводимы, а ALTER (drop/rename constraint) не зависел от авто-имён БД.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей; metadata используется Alembic."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """created_at в UTC (конвенция: храним UTC, отображаем Asia/Tashkent)."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


engine: AsyncEngine = create_async_engine(get_settings().database_url, echo=get_settings().debug)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI-зависимость: одна сессия на запрос."""
    async with session_factory() as session:
        yield session
