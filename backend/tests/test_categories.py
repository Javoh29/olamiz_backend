"""Каталог: дерево категорий, сиды (идемпотентность), эндпоинт."""

import fakeredis.aioredis
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.catalog import service
from app.domain.catalog.models import Category
from app.seed.categories import CATEGORY_TREE, seed_categories


async def test_seed_builds_tree(session: AsyncSession) -> None:
    await seed_categories(session)
    roots = await service.list_category_tree(session)
    assert len(roots) == len(CATEGORY_TREE)
    # у каждого корня — свои подкатегории, depth=2
    first = roots[0]
    assert first.depth == 1
    assert len(first.children) == len(CATEGORY_TREE[0][3])
    assert all(child.depth == 2 for child in first.children)


async def test_seed_idempotent(session: AsyncSession) -> None:
    await seed_categories(session)
    await seed_categories(session)
    total = await session.scalar(select(func.count()).select_from(Category))
    expected = sum(1 + len(children) for _, _, _, children in CATEGORY_TREE)
    assert total == expected


async def test_categories_endpoint(
    client: AsyncClient, session: AsyncSession, redis: fakeredis.aioredis.FakeRedis
) -> None:
    await seed_categories(session)
    await session.commit()
    resp = await client.get("/api/v1/catalog/categories")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == len(CATEGORY_TREE)
    assert body[0]["slug"] == CATEGORY_TREE[0][0]
    assert body[0]["children"][0]["name_ru"] == CATEGORY_TREE[0][3][0][1]
