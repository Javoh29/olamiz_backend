"""Конфигурация приложения (pydantic-settings).

Все параметры — из env (контракт: deploy/.env.example), см. docs/backend.md §9.
Интервалы эскалаций и веса ранжирования — конфиг, не хардкод.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Приложение ---
    debug: bool = False
    base_url: str = "https://rento.uz"
    display_timezone: str = "Asia/Tashkent"  # хранение — всегда UTC

    # --- Инфраструктура ---
    database_url: str = "postgresql+asyncpg://rento:rento@localhost:5432/rento"
    redis_url: str = "redis://localhost:6379/0"

    # --- Auth: JWT + OTP ---
    jwt_secret: str = "change-me"
    jwt_access_ttl_min: int = 30
    jwt_refresh_ttl_days: int = 30
    otp_ttl_min: int = 5
    otp_rate_per_phone_hour: int = 3
    otp_rate_per_ip_hour: int = 10

    # --- Тайминги сделки и эскалаций ---
    escalate_sms_min: int = 3
    escalate_call_min: int = 7  # автозвонок — v1.1
    alternatives_min: int = 15
    booking_expire_h: int = 24
    auto_complete_days: int = 3
    review_blind_days: int = 7
    max_rent_days: int = 30

    # --- Веса ранжирования каталога (architecture.md §7); стартовые, тюнятся по данным ---
    rank_w1: float = 0.3  # скорость ответа прокатчика
    rank_w2: float = 0.3  # рейтинг прокатчика и карточки
    rank_w3: float = 0.2  # полнота карточки
    rank_w4: float = 0.2  # штраф за отмены прокатчиком

    # --- SMS (провайдер конфигурируется: Eskiz / PlayMobile) ---
    sms_provider: Literal["eskiz", "playmobile"] = "eskiz"
    eskiz_email: str = ""
    eskiz_password: str = ""
    playmobile_login: str = ""
    playmobile_password: str = ""

    # --- S3 / MinIO (фото карточек и чек-листов; хранение только в УЗ) ---
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "rento"

    # --- Наблюдаемость ---
    sentry_dsn: str = ""

    # --- Telegram-бот прокатчика ---
    tg_bot_token: str = ""
    tg_webhook_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
