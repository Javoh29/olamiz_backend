"""Бизнес-логика каталога: дерево категорий, карточки и units."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.catalog.models import Category, DepositKind, Listing, ListingStatus, Unit


async def list_category_tree(session: AsyncSession) -> list[Category]:
    """Корневые категории с подкатегориями (до 3 уровней), отсортированные по sort."""
    result = await session.scalars(
        select(Category)
        .where(Category.parent_id.is_(None))
        .order_by(Category.sort)
        .options(selectinload(Category.children).selectinload(Category.children))
    )
    return list(result)


async def ensure_units(session: AsyncSession, listing: Listing) -> None:
    """Создать недостающие units до listing.quantity (units в MVP не видны — задел под учёт).

    Идемпотентно: создаёт только нехватающие; при уменьшении quantity лишние не трогает
    (выбытие единиц — через status=retired отдельно).
    """
    existing = await session.scalar(
        select(func.count()).select_from(Unit).where(Unit.listing_id == listing.id)
    )
    for _ in range(listing.quantity - (existing or 0)):
        session.add(Unit(listing_id=listing.id))
    await session.flush()


async def create_listing(
    session: AsyncSession,
    *,
    supplier_id: int,
    category_id: int,
    title: str,
    price_per_day: int,
    slug: str,
    description: str | None = None,
    deposit_kind: DepositKind = DepositKind.none,
    deposit_amount: int | None = None,
    quantity: int = 1,
    status: ListingStatus = ListingStatus.draft,
) -> Listing:
    """Создать карточку и синхронно завести units по quantity."""
    listing = Listing(
        supplier_id=supplier_id,
        category_id=category_id,
        title=title,
        price_per_day=price_per_day,
        slug=slug,
        description=description,
        deposit_kind=deposit_kind,
        deposit_amount=deposit_amount,
        quantity=quantity,
        status=status,
    )
    session.add(listing)
    await session.flush()
    await ensure_units(session, listing)
    return listing
