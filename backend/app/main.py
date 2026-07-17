"""Сборка FastAPI-приложения: REST API, Telegram-webhook, SSR-витрина, админка.

Адаптеры тонкие, вся бизнес-логика — в app/domain (architecture.md §2).
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.admin.setup import init_admin
from app.api.v1.errors import ApiError, api_error_handler
from app.api.v1.router import api_router
from app.bot.webhook import router as bot_router
from app.web.router import router as web_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Olamiz API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(bot_router)
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "web" / "static"),
        name="static",
    )
    app.include_router(web_router)
    init_admin(app)
    return app


app = create_app()
