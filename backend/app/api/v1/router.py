"""Корневой роутер REST API v1; доменные роутеры подключаются сюда (backend.md §5)."""

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health", tags=["service"])
async def health() -> dict[str, str]:
    """Healthcheck для мониторинга и smoke-тестов."""
    return {"status": "ok"}
