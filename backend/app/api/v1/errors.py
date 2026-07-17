"""Единый формат ошибок API: {code, message_ru, message_uz} (backend.md §5)."""

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message_ru: str, message_uz: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message_ru = message_ru
        self.message_uz = message_uz
        super().__init__(code)


async def api_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)  # регистрируется только на ApiError
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message_ru": exc.message_ru, "message_uz": exc.message_uz},
    )


def otp_rate_limited() -> ApiError:
    return ApiError(
        429,
        "otp_rate_limited",
        "Слишком много запросов кода. Попробуйте позже.",
        "Kod so'rovlari juda ko'p. Keyinroq urinib ko'ring.",
    )


def otp_invalid() -> ApiError:
    return ApiError(
        400,
        "otp_invalid",
        "Неверный или просроченный код.",
        "Kod noto'g'ri yoki muddati o'tgan.",
    )


def token_invalid() -> ApiError:
    return ApiError(
        401,
        "token_invalid",
        "Сессия недействительна. Войдите снова.",
        "Sessiya yaroqsiz. Qaytadan kiring.",
    )


def unauthorized() -> ApiError:
    return ApiError(
        401,
        "unauthorized",
        "Требуется авторизация.",
        "Avtorizatsiya talab qilinadi.",
    )
