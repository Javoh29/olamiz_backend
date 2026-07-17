"""Тестовый харнесс: изолированная БД (savepoint-rollback на тест), fakeredis, httpx-клиент.

Каждый тест работает во вложенной транзакции, которая откатывается — данные не текут
между тестами. Redis подменяется на fakeredis, get_session/get_redis — через
dependency_overrides FastAPI.
"""

from collections.abc import AsyncIterator, Iterator

import asyncpg
import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app import models as _models  # noqa: F401  # наполняет Base.metadata всеми таблицами
from app.core.config import get_settings
from app.core.db import Base, get_session
from app.core.redis import get_redis
from app.main import app

TEST_DB_NAME = "olamiz_test"


def _urls() -> tuple[str, str]:
    """(admin_dsn для asyncpg к postgres, sqlalchemy-url тестовой БД)."""
    db_url = get_settings().database_url
    prefix = db_url.rsplit("/", 1)[0]
    admin_dsn = f"{prefix.replace('+asyncpg', '')}/postgres"
    test_url = f"{prefix}/{TEST_DB_NAME}"
    return admin_dsn, test_url


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    admin_dsn, test_url = _urls()
    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME)
        if not exists:
            await conn.execute(f"CREATE DATABASE {TEST_DB_NAME} OWNER olamiz")
    finally:
        await conn.close()

    engine = create_async_engine(test_url)
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    conn = await engine.connect()
    trans = await conn.begin()
    db = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
    try:
        yield db
    finally:
        await db.close()
        await trans.rollback()
        await conn.close()


@pytest.fixture
def redis() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
async def client(
    session: AsyncSession, redis: fakeredis.aioredis.FakeRedis
) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_redis] = lambda: redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()
