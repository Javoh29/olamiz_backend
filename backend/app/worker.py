"""ARQ worker: отложенные задачи и cron.

Бизнес-задач пока нет — эскалации, expire_booking, auto_complete,
publish_reviews и пересчёт метрик появятся вместе с domain-логикой
(backend.md §4). `ping` — технологическая smoke-задача: ARQ требует
хотя бы одну зарегистрированную функцию.
"""

from collections.abc import Callable
from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings


async def ping(ctx: dict[str, Any]) -> str:
    return "pong"


class WorkerSettings:
    functions: ClassVar[list[Callable[..., Any]]] = [ping]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
