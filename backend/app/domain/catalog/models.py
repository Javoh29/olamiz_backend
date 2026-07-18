"""ORM-модели каталога: категории, карточки (listing), фото, units.

Дерево категорий создаёт и контролирует платформа (D11): прокатчик их не создаёт.
Карточка = модель инструмента у прокатчика + количество; бронь резервирует единицу
из пула (D11). unit — физическая единица, в MVP наружу не видна (задел под инвентарный
учёт), создаётся автоматически по quantity. Названия — ru/uz, slug уникален (SEO-URL).
"""

import enum
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.domain.suppliers.models import Supplier


class DepositKind(enum.StrEnum):
    money = "money"  # денежный залог (deposit_amount)
    passport = "passport"  # под паспорт
    none = "none"  # без залога


class ListingStatus(enum.StrEnum):
    draft = "draft"
    moderation = "moderation"
    active = "active"
    hidden = "hidden"


class UnitStatus(enum.StrEnum):
    active = "active"
    repair = "repair"
    retired = "retired"


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (CheckConstraint("depth BETWEEN 1 AND 3", name="depth_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    name_ru: Mapped[str] = mapped_column(String(120))
    name_uz: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True)
    depth: Mapped[int] = mapped_column(Integer, server_default="1")
    sort: Mapped[int] = mapped_column(Integer, server_default="0")

    parent: Mapped["Category | None"] = relationship(
        remote_side="Category.id", back_populates="children"
    )
    children: Mapped[list["Category"]] = relationship(
        back_populates="parent", order_by="Category.sort"
    )


class Listing(TimestampMixin, Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        # Частый фильтр витрины/каталога: активные карточки по категории.
        Index("ix_listings_category_status", "category_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True
    )
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    # Деньги — целые сумы (в UZS дробей на практике нет).
    price_per_day: Mapped[int] = mapped_column(BigInteger)
    deposit_kind: Mapped[DepositKind] = mapped_column(
        Enum(DepositKind, native_enum=False, length=12, create_constraint=True),
        server_default=DepositKind.none.value,
    )
    deposit_amount: Mapped[int | None] = mapped_column(BigInteger)
    quantity: Mapped[int] = mapped_column(Integer, server_default="1")
    status: Mapped[ListingStatus] = mapped_column(
        Enum(ListingStatus, native_enum=False, length=12, create_constraint=True),
        server_default=ListingStatus.draft.value,
    )
    # Метрики карточки — пересчитывает worker из отзывов; у новичка пустые.
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    fits_photo_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    slug: Mapped[str] = mapped_column(String(160), unique=True)

    supplier: Mapped["Supplier"] = relationship()
    category: Mapped["Category"] = relationship()
    photos: Mapped[list["ListingPhoto"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", order_by="ListingPhoto.sort"
    )
    units: Mapped[list["Unit"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )


class ListingPhoto(Base):
    __tablename__ = "listing_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(500))
    sort: Mapped[int] = mapped_column(Integer, server_default="0")

    listing: Mapped["Listing"] = relationship(back_populates="photos")


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    inventory_no: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[UnitStatus] = mapped_column(
        Enum(UnitStatus, native_enum=False, length=12, create_constraint=True),
        server_default=UnitStatus.active.value,
    )

    listing: Mapped["Listing"] = relationship(back_populates="units")
