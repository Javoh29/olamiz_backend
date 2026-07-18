"""Стартовое дерево категорий (2 уровня). Платформа контролирует каталог (D11).

Идемпотентно: get-or-create по уникальному slug.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.catalog.models import Category

# (slug, name_ru, name_uz, [подкатегории: (slug, name_ru, name_uz)])
CATEGORY_TREE: list[tuple[str, str, str, list[tuple[str, str, str]]]] = [
    (
        "elektroinstrument",
        "Электроинструмент",
        "Elektr asboblar",
        [
            ("perforatory-dreli", "Перфораторы и дрели", "Perforator va drellar"),
            ("bolgarki", "Болгарки (УШМ)", "Bolgarkalar (UShM)"),
            ("shurupoverty", "Шуруповёрты", "Shuruppa mashinalari"),
            ("lobziki-pily", "Лобзики и пилы", "Elektr arralar"),
        ],
    ),
    (
        "stroy-oborudovanie",
        "Строительное оборудование",
        "Qurilish uskunalari",
        [
            ("generatory", "Генераторы", "Generatorlar"),
            ("vibroplity", "Виброплиты", "Vibroplitalar"),
            ("betonomeshalki", "Бетономешалки", "Beton aralashtirgichlar"),
            ("svarochnye-apparaty", "Сварочные аппараты", "Payvandlash apparatlari"),
        ],
    ),
    (
        "sadovaya-tehnika",
        "Садовая техника",
        "Bog' texnikasi",
        [
            ("gazonokosilki", "Газонокосилки", "Maysa o'rgichlar"),
            ("trimmery", "Триммеры", "Trimmerlar"),
        ],
    ),
    (
        "izmeritelnyy-instrument",
        "Измерительный инструмент",
        "O'lchov asboblari",
        [
            ("lazernye-urovni", "Лазерные уровни", "Lazerli nivelirlar"),
        ],
    ),
]


async def _get_or_create(
    session: AsyncSession,
    *,
    slug: str,
    name_ru: str,
    name_uz: str,
    depth: int,
    parent_id: int | None,
    sort: int,
) -> Category:
    category = (await session.scalars(select(Category).where(Category.slug == slug))).first()
    if category is None:
        category = Category(
            slug=slug,
            name_ru=name_ru,
            name_uz=name_uz,
            depth=depth,
            parent_id=parent_id,
            sort=sort,
        )
        session.add(category)
        await session.flush()
    return category


async def seed_categories(session: AsyncSession) -> None:
    """Наполнить дерево категорий. Идемпотентно."""
    for root_sort, (slug, name_ru, name_uz, children) in enumerate(CATEGORY_TREE):
        root = await _get_or_create(
            session,
            slug=slug,
            name_ru=name_ru,
            name_uz=name_uz,
            depth=1,
            parent_id=None,
            sort=root_sort,
        )
        for child_sort, (cslug, cname_ru, cname_uz) in enumerate(children):
            await _get_or_create(
                session,
                slug=cslug,
                name_ru=cname_ru,
                name_uz=cname_uz,
                depth=2,
                parent_id=root.id,
                sort=child_sort,
            )
