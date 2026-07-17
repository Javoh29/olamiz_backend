"""ORM-модели прокатчиков (architecture.md §3).

Прокатчики создаются ручным онбордингом из админки (D2/D8), привязка Telegram —
по одноразовому коду (tg_chat_id). Паспорт/ИНН/реквизиты вынесены в отдельную
таблицу supplier_private с ограниченным доступом — из публичного API недоступны.
Метрики (response_median_sec, rating, requests_count) пересчитывает ARQ worker.
"""

import enum
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.domain.geo.models import District


class LegalType(enum.StrEnum):
    individual = "individual"  # частник
    legal = "legal"  # юрлицо


class SupplierStatus(enum.StrEnum):
    active = "active"
    paused = "paused"


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255))
    legal_type: Mapped[LegalType] = mapped_column(
        Enum(LegalType, native_enum=False, length=20, create_constraint=True)
    )
    phone: Mapped[str] = mapped_column(String(20))
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    has_delivery: Mapped[bool] = mapped_column(Boolean, server_default="false")

    # Привязка Telegram-бота (бренд Beramiz): один tg-аккаунт = один прокатчик.
    tg_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)

    status: Mapped[SupplierStatus] = mapped_column(
        Enum(SupplierStatus, native_enum=False, length=20, create_constraint=True),
        server_default=SupplierStatus.active.value,
    )

    # Метрики — пересчитывает worker; у новичка пустые (нейтральные в ранжировании).
    response_median_sec: Mapped[int | None] = mapped_column(Integer)
    requests_count: Mapped[int] = mapped_column(Integer, server_default="0")
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))

    district: Mapped["District"] = relationship()
    private: Mapped["SupplierPrivate | None"] = relationship(
        back_populates="supplier", cascade="all, delete-orphan"
    )


class SupplierPrivate(TimestampMixin, Base):
    """Чувствительные реквизиты прокатчика: только админка, не публичное API."""

    __tablename__ = "supplier_private"

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), primary_key=True
    )
    passport: Mapped[str | None] = mapped_column(String(50))
    inn: Mapped[str | None] = mapped_column(String(20))
    requisites: Mapped[str | None] = mapped_column(Text)

    supplier: Mapped["Supplier"] = relationship(back_populates="private")
