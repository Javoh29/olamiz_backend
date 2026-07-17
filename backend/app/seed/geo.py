"""Стартовый гео-справочник: город Ташкент и его районы (туманы).

Мультирегиональность заложена структурой region → city → district (D3);
пилот ограничен одним районом операционно, но данные наполняем полностью,
чтобы каталог и онбординг сразу работали в разрезе районов.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.geo.models import City, District, Region

# Регион верхнего уровня = город республиканского подчинения Ташкент.
TASHKENT_RU = "Ташкент"
TASHKENT_UZ = "Toshkent"

# 12 районов Ташкента (ru, uz). Кандидаты пилота (Юнусабад/Сергели/Чиланзар) — в общем списке.
TASHKENT_DISTRICTS: list[tuple[str, str]] = [
    ("Бектемир", "Bektemir"),
    ("Мирабад", "Mirobod"),
    ("Мирзо-Улугбек", "Mirzo-Ulug'bek"),
    ("Сергели", "Sergeli"),
    ("Учтепа", "Uchtepa"),
    ("Чиланзар", "Chilonzor"),
    ("Шайхантаур", "Shayxontohur"),
    ("Юнусабад", "Yunusobod"),
    ("Яккасарай", "Yakkasaroy"),
    ("Яшнабад", "Yashnobod"),
    ("Алмазар", "Olmazor"),
    ("Янгихаёт", "Yangihayot"),
]


async def _get_or_create_region(session: AsyncSession, name_ru: str, name_uz: str) -> Region:
    region = (await session.scalars(select(Region).where(Region.name_ru == name_ru))).first()
    if region is None:
        region = Region(name_ru=name_ru, name_uz=name_uz)
        session.add(region)
        await session.flush()
    return region


async def _get_or_create_city(
    session: AsyncSession, region: Region, name_ru: str, name_uz: str
) -> City:
    city = (
        await session.scalars(
            select(City).where(City.region_id == region.id, City.name_ru == name_ru)
        )
    ).first()
    if city is None:
        city = City(region_id=region.id, name_ru=name_ru, name_uz=name_uz)
        session.add(city)
        await session.flush()
    return city


async def _get_or_create_district(
    session: AsyncSession, city: City, name_ru: str, name_uz: str
) -> District:
    district = (
        await session.scalars(
            select(District).where(District.city_id == city.id, District.name_ru == name_ru)
        )
    ).first()
    if district is None:
        district = District(city_id=city.id, name_ru=name_ru, name_uz=name_uz)
        session.add(district)
        await session.flush()
    return district


async def seed_geo(session: AsyncSession) -> None:
    """Наполнить гео-справочник Ташкентом и районами. Идемпотентно."""
    region = await _get_or_create_region(session, TASHKENT_RU, TASHKENT_UZ)
    city = await _get_or_create_city(session, region, TASHKENT_RU, TASHKENT_UZ)
    for name_ru, name_uz in TASHKENT_DISTRICTS:
        await _get_or_create_district(session, city, name_ru, name_uz)
