"""API каталога: лента /listings (только active, фильтры), деталка /{id} (скрытие телефона)."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.catalog import service
from app.domain.catalog.models import Category, ListingStatus
from app.domain.geo.models import District
from app.domain.suppliers.models import LegalType, Supplier
from app.seed.categories import seed_categories
from app.seed.geo import seed_geo

SUPPLIER_PHONE = "+998901112233"


async def _seed_supplier(session: AsyncSession, *, phone: str = SUPPLIER_PHONE) -> Supplier:
    await seed_geo(session)
    district_id = await session.scalar(select(District.id).order_by(District.id).limit(1))
    supplier = Supplier(
        display_name="Прокат №1",
        legal_type=LegalType.individual,
        phone=phone,
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


async def test_listings_returns_only_active(client: AsyncClient, session: AsyncSession) -> None:
    supplier = await _seed_supplier(session)
    category_id = await _leaf_category_id(session)
    await service.create_listing(
        session,
        supplier_id=supplier.id,
        category_id=category_id,
        title="Перфоратор Bosch",
        price_per_day=50000,
        slug="perforator-bosch-1",
        status=ListingStatus.active,
    )
    await service.create_listing(
        session,
        supplier_id=supplier.id,
        category_id=category_id,
        title="Черновик карточки",
        price_per_day=1000,
        slug="draft-1",
    )  # status=draft по умолчанию — в выдаче быть не должно

    resp = await client.get("/api/v1/catalog/listings")
    assert resp.status_code == 200
    titles = [item["title"] for item in resp.json()]
    assert "Перфоратор Bosch" in titles
    assert "Черновик карточки" not in titles


async def test_listings_filter_by_query(client: AsyncClient, session: AsyncSession) -> None:
    supplier = await _seed_supplier(session)
    category_id = await _leaf_category_id(session)
    await service.create_listing(
        session,
        supplier_id=supplier.id,
        category_id=category_id,
        title="Перфоратор Bosch",
        price_per_day=50000,
        slug="perforator-bosch-2",
        status=ListingStatus.active,
    )
    await service.create_listing(
        session,
        supplier_id=supplier.id,
        category_id=category_id,
        title="Болгарка Makita",
        price_per_day=30000,
        slug="bolgarka-makita-2",
        status=ListingStatus.active,
    )

    resp = await client.get("/api/v1/catalog/listings", params={"q": "болгарка"})
    assert resp.status_code == 200
    titles = [item["title"] for item in resp.json()]
    assert titles == ["Болгарка Makita"]


async def test_listing_detail_hides_phone_without_booking(
    client: AsyncClient, session: AsyncSession
) -> None:
    supplier = await _seed_supplier(session)
    category_id = await _leaf_category_id(session)
    listing = await service.create_listing(
        session,
        supplier_id=supplier.id,
        category_id=category_id,
        title="Перфоратор Bosch",
        price_per_day=50000,
        slug="perforator-bosch-3",
        status=ListingStatus.active,
    )

    resp = await client.get(f"/api/v1/catalog/listings/{listing.id}")
    assert resp.status_code == 200
    body = resp.json()
    # Телефон скрыт: подтверждённой брони нет (booking-модуля пока нет).
    assert body["supplier"]["phone"] is None
    assert body["supplier"]["display_name"] == "Прокат №1"
    assert body["photos"] == []


async def test_listing_detail_404_for_draft(client: AsyncClient, session: AsyncSession) -> None:
    supplier = await _seed_supplier(session)
    category_id = await _leaf_category_id(session)
    listing = await service.create_listing(
        session,
        supplier_id=supplier.id,
        category_id=category_id,
        title="Черновик",
        price_per_day=1000,
        slug="draft-detail-1",
    )  # draft → в публичной деталке 404

    resp = await client.get(f"/api/v1/catalog/listings/{listing.id}")
    assert resp.status_code == 404
    assert resp.json()["code"] == "listing_not_found"
