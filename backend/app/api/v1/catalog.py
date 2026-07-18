"""Каталог: категории, лента карточек, деталка (backend.md §5).

Хендлеры тонкие: фильтрация/поиск — в domain/catalog.service, порядок выдачи —
domain/catalog.ranking, скрытие телефона — domain-предикат. Здесь только сборка ответа
(маппинг ORM→схема + presigned-ссылки на фото).
"""

from fastapi import APIRouter, Query

from app.api.v1.deps import OptionalUser, SessionDep
from app.api.v1.errors import listing_not_found
from app.api.v1.schemas import (
    CategoryOut,
    ListingDetailOut,
    ListingItemOut,
    SupplierPublicOut,
)
from app.core import storage
from app.domain.catalog import ranking, service
from app.domain.catalog.models import Listing

router = APIRouter(prefix="/catalog", tags=["catalog"])

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50


@router.get("/categories", response_model=list[CategoryOut])
async def categories(session: SessionDep) -> list[CategoryOut]:
    tree = await service.list_category_tree(session)
    return [CategoryOut.model_validate(node) for node in tree]


@router.get("/listings", response_model=list[ListingItemOut])
async def listings(
    session: SessionDep,
    category: int | None = None,
    district: int | None = None,
    q: str | None = None,
    limit: int = Query(_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> list[ListingItemOut]:
    found = await service.search_listings(session, category_id=category, district_id=district, q=q)
    # Порядок — по score (architecture.md §7). Масштаб MVP смешной: сортируем в приложении.
    weights = ranking.weights_from_settings()
    found.sort(
        key=lambda item: ranking.score(ranking.signals_from_listing(item), weights),
        reverse=True,
    )
    page = found[offset : offset + limit]
    return [await _to_item(item) for item in page]


@router.get("/listings/{listing_id}", response_model=ListingDetailOut)
async def listing_detail(
    listing_id: int, session: SessionDep, user: OptionalUser
) -> ListingDetailOut:
    listing = await service.get_active_listing(session, listing_id)
    if listing is None:
        raise listing_not_found()
    show_phone = await service.supplier_phone_visible(
        session, user_id=user.id if user else None, listing_id=listing.id
    )
    return await _to_detail(listing, show_phone=show_phone)


async def _to_item(listing: Listing) -> ListingItemOut:
    thumbnail = await storage.presigned_get(listing.photos[0].url) if listing.photos else None
    return ListingItemOut(
        id=listing.id,
        title=listing.title,
        price_per_day=listing.price_per_day,
        deposit_kind=listing.deposit_kind,
        deposit_amount=listing.deposit_amount,
        rating=listing.rating,
        district_id=listing.supplier.district_id,
        supplier_name=listing.supplier.display_name,
        thumbnail=thumbnail,
    )


async def _to_detail(listing: Listing, *, show_phone: bool) -> ListingDetailOut:
    photos = await storage.presigned_get_many([photo.url for photo in listing.photos])
    supplier = SupplierPublicOut(
        id=listing.supplier.id,
        display_name=listing.supplier.display_name,
        district_id=listing.supplier.district_id,
        rating=listing.supplier.rating,
        phone=listing.supplier.phone if show_phone else None,
    )
    return ListingDetailOut(
        id=listing.id,
        title=listing.title,
        description=listing.description,
        price_per_day=listing.price_per_day,
        deposit_kind=listing.deposit_kind,
        deposit_amount=listing.deposit_amount,
        quantity=listing.quantity,
        rating=listing.rating,
        fits_photo_pct=listing.fits_photo_pct,
        slug=listing.slug,
        category_id=listing.category_id,
        photos=photos,
        supplier=supplier,
    )
