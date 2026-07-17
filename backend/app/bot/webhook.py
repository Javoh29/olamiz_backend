"""Webhook-заглушка Telegram-бота прокатчика (aiogram 3, бренд Beramiz).

Бот живёт в том же процессе, что и API (architecture.md §1): апдейты приходят
на /tg/webhook и скармливаются диспетчеру. Роутеры бота (заявки, чек-листы,
команды) появятся вместе с domain-логикой. Все тексты бота — от имени Beramiz,
Olamiz упоминается как клиентская витрина (backend.md §6); словари ru/uz.
"""

from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.core.config import get_settings

router = APIRouter(tags=["telegram"], include_in_schema=False)

dp = Dispatcher()  # aiogram-роутеры подключаются сюда: dp.include_router(...)

_bot: Bot | None = None


def get_bot() -> Bot:
    """Ленивая инициализация: без TG_BOT_TOKEN (локальная разработка, тесты) бот выключен."""
    global _bot
    token = get_settings().tg_bot_token
    if not token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Telegram bot is not configured")
    if _bot is None:
        _bot = Bot(token=token)
    return _bot


@router.post("/tg/webhook")
async def tg_webhook(
    request: Request,
    secret: Annotated[str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = None,
) -> Response:
    settings = get_settings()
    if settings.tg_webhook_secret and secret != settings.tg_webhook_secret:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    bot = get_bot()
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return Response(status_code=status.HTTP_200_OK)
