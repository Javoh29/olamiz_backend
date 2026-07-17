"""Корневой роутер REST API v1; доменные роутеры подключаются сюда (backend.md §5)."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.me import router as me_router

api_router = APIRouter()


@api_router.get("/health", tags=["service"])
async def health() -> dict[str, str]:
    """Healthcheck для мониторинга и smoke-тестов."""
    return {"status": "ok"}


api_router.include_router(auth_router)
api_router.include_router(me_router)
