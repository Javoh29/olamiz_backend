"""SMS-шлюз: интерфейс `SmsGateway` + dev-заглушка.

Провайдер конфигурируется (Eskiz/PlayMobile) — реализации появятся отдельно.
В dev/тестах используется LogSmsGateway: не шлёт реальные SMS, пишет в лог.
"""

import logging
from typing import Protocol

logger = logging.getLogger("olamiz.sms")


class SmsGateway(Protocol):
    async def send(self, phone: str, text: str) -> None: ...


class LogSmsGateway:
    """Заглушка: пишет SMS в лог вместо реальной отправки."""

    async def send(self, phone: str, text: str) -> None:
        logger.info("SMS -> %s: %s", phone, text)
