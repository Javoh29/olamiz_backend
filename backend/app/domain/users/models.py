"""ORM-модели клиентов (architecture.md §3).

Клиент регистрируется по телефону + OTP (D12), паспорт на уровне платформы не
требуется. Рейтинг и число сделок пересчитываются из истории (reviews/booking).
offer_acceptances — акцепт публичной оферты: клиент при регистрации либо прокатчик
на онбординге (ровно один из user_id/supplier_id заполнен).
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class UserLanguage(enum.StrEnum):
    ru = "ru"
    uz = "uz"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[UserLanguage] = mapped_column(
        Enum(UserLanguage, native_enum=False, length=8, create_constraint=True),
        server_default=UserLanguage.ru.value,
    )
    # Метрики клиента — пересчитываются из истории сделок/отзывов; у новичка пустые.
    client_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    deals_count: Mapped[int] = mapped_column(Integer, server_default="0")


class OfferAcceptance(Base):
    """Факт акцепта версии оферты. Актор — клиент ИЛИ прокатчик (ровно один)."""

    __tablename__ = "offer_acceptances"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NULL) <> (supplier_id IS NULL)",
            name="actor",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), index=True
    )
    offer_version: Mapped[str] = mapped_column(String(50))
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
