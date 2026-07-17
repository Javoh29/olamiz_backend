"""Минимальный словарь локализации (ru/uz).

Тексты пользователю (SMS, бот, app) не хардкодятся в коде — только здесь.
По мере роста ключи разъедутся по доменам (notifications), пока — общий словарь.
"""

from typing import Literal

Lang = Literal["ru", "uz"]

MESSAGES: dict[str, dict[Lang, str]] = {
    "otp_code": {
        "ru": "Код для входа в Olamiz: {code}",
        "uz": "Olamiz'ga kirish uchun kod: {code}",
    },
}


def t(key: str, lang: Lang = "ru", **params: object) -> str:
    """Отрендерить сообщение по ключу и языку (fallback на ru)."""
    variants = MESSAGES[key]
    template = variants.get(lang, variants["ru"])
    return template.format(**params)
