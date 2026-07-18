"""S3/MinIO: presigned-ссылки на фото (backend.md §5, architecture.md §10).

Фото карточек и чек-листов лежат в MinIO on-prem (ПД — только в УЗ, не внешний SaaS).
Загрузка объектов идёт server-side (API multipart / бот пишут по ключу), наружу отдаём
presigned GET на чтение — ключ не раскрывает доступы к бакету. Presign — локальная
подпись (SigV4), без похода в S3, поэтому дёшев и тестируется без живого сервера.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aioboto3
from botocore.config import Config

from app.core.config import get_settings

_session = aioboto3.Session()
# SigV4 — актуальный формат подписи (SigV2 устарел); MinIO поддерживает.
_config = Config(signature_version="s3v4")

DEFAULT_EXPIRES_SEC = 3600


@asynccontextmanager
async def _client() -> AsyncIterator[Any]:
    s = get_settings()
    async with _session.client(
        "s3",
        endpoint_url=s.s3_endpoint,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name="us-east-1",
        config=_config,
    ) as client:
        yield client


async def presigned_get(key: str, *, expires_sec: int = DEFAULT_EXPIRES_SEC) -> str:
    """Presigned GET-URL на чтение объекта из бакета."""
    async with _client() as client:
        return await _presign(client, key, expires_sec)


async def presigned_get_many(
    keys: list[str], *, expires_sec: int = DEFAULT_EXPIRES_SEC
) -> list[str]:
    """Presigned-ссылки на набор ключей одним клиентом (галерея фото карточки)."""
    if not keys:
        return []
    async with _client() as client:
        return [await _presign(client, key, expires_sec) for key in keys]


async def _presign(client: Any, key: str, expires_sec: int) -> str:
    bucket = get_settings().s3_bucket
    url: str = await client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_sec,
    )
    return url
