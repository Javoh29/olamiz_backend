"""Бизнес-логика каталога: дерево категорий, карточки, units, поиск и видимость контактов."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.catalog.models import Category, DepositKind, Listing, ListingStatus, Unit
from app.domain.suppliers.models import Supplier


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


async def search_listings(
    session: AsyncSession,
    *,
    category_id: int | None = None,
    district_id: int | None = None,
    q: str | None = None,
) -> list[Listing]:
    """Активные карточки под фильтры каталога (backend.md §5).

    Сортировка по score и пагинация — на уровне выдачи (см. domain/catalog/ranking).
    Фильтр по категории — точное совпадение (раскрытие в поддерево — задел на потом);
    поиск по названию — простой ILIKE (полнотекст по title — позже).
    Район берётся у прокатчика (у карточки своего района нет).
    """
    stmt = (
        select(Listing)
        .where(Listing.status == ListingStatus.active)
        .options(selectinload(Listing.supplier), selectinload(Listing.photos))
    )
    if category_id is not None:
        stmt = stmt.where(Listing.category_id == category_id)
    if district_id is not None:
        stmt = stmt.join(Supplier, Listing.supplier_id == Supplier.id).where(
            Supplier.district_id == district_id
        )
    if q:
        stmt = stmt.where(Listing.title.ilike(f"%{q}%"))
    result = await session.scalars(stmt)
    return list(result)


async def get_active_listing(session: AsyncSession, listing_id: int) -> Listing | None:
    """Активная карточка по id с загруженными supplier и photos (для деталки)."""
    stmt = (
        select(Listing)
        .where(Listing.id == listing_id, Listing.status == ListingStatus.active)
        .options(selectinload(Listing.supplier), selectinload(Listing.photos))
    )
    return (await session.scalars(stmt)).first()


async def supplier_phone_visible(
    session: AsyncSession, *, user_id: int | None, listing_id: int
) -> bool:
    """Телефон прокатчика виден только клиенту с подтверждённой бронью этой карточки (D1).

    Booking-модуля ещё нет → подтверждённых броней не существует, всегда False.
    Станет запросом к bookings(status ∈ confirmed/active) при появлении модуля брони.
    """
    return False
