"""Бизнес-логика каталога: чтение дерева категорий."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.catalog.models import Category


async def list_category_tree(session: AsyncSession) -> list[Category]:
    """Корневые категории с подкатегориями (до 3 уровней), отсортированные по sort."""
    result = await session.scalars(
        select(Category)
        .where(Category.parent_id.is_(None))
        .order_by(Category.sort)
        .options(selectinload(Category.children).selectinload(Category.children))
    )
    return list(result)
