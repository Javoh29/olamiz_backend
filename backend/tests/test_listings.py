"""Карточки: авто-создание units по quantity, идемпотентность, CHECK quantity."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.catalog import service
from app.domain.catalog.models import Category, Listing, Unit
from app.domain.geo.models import District
from app.domain.suppliers.models import LegalType, Supplier
from app.seed.categories import seed_categories
from app.seed.geo import seed_geo


async def _make_supplier(session: AsyncSession) -> Supplier:
    await seed_geo(session)
    district_id = await session.scalar(select(District.id).order_by(District.id).limit(1))
    supplier = Supplier(
        display_name="Прокат №1",
        legal_type=LegalType.individual,
        phone="+998901112233",
        district_id=district_id,
    )
    session.add(supplier)
    await session.flush()
    return supplier


async def _leaf_category_id(session: AsyncSession) -> int:
    await seed_categories(session)
    cat_id = await session.scalar(
        select(Category.id).where(Category.parent_id.is_not(None)).order_by(Category.id).limit(1)
    )
    assert cat_id is not None
    return cat_id


async def _units_count(session: AsyncSession, listing_id: int) -> int:
    count = await session.scalar(
        select(func.count()).select_from(Unit).where(Unit.listing_id == listing_id)
    )
    return count or 0


async def test_create_listing_creates_units(session: AsyncSession) -> None:
    supplier = await _make_supplier(session)
    category_id = await _leaf_category_id(session)
    listing = await service.create_listing(
        session,
        supplier_id=supplier.id,
        category_id=category_id,
        title="Перфоратор Bosch GBH 2-26",
        price_per_day=50000,
        slug="perforator-bosch-gbh-2-26-1",
        quantity=3,
    )
    assert await _units_count(session, listing.id) == 3


async def test_ensure_units_idempotent_and_grows(session: AsyncSession) -> None:
    supplier = await _make_supplier(session)
    category_id = await _leaf_category_id(session)
    listing = await service.create_listing(
        session,
        supplier_id=supplier.id,
        category_id=category_id,
        title="Болгарка Makita",
        price_per_day=30000,
        slug="bolgarka-makita-1",
        quantity=2,
    )
    assert await _units_count(session, listing.id) == 2

    # повторный вызов не плодит лишних
    await service.ensure_units(session, listing)
    assert await _units_count(session, listing.id) == 2

    # рост quantity → добираются недостающие
    listing.quantity = 4
    await service.ensure_units(session, listing)
    assert await _units_count(session, listing.id) == 4


async def test_quantity_must_be_positive(session: AsyncSession) -> None:
    supplier = await _make_supplier(session)
    category_id = await _leaf_category_id(session)
    session.add(
        Listing(
            supplier_id=supplier.id,
            category_id=category_id,
            title="Плохая карточка",
            price_per_day=1000,
            slug="bad-listing-1",
            quantity=0,
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()
