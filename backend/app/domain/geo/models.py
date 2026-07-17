"""ORM-модели гео-справочников: регион → город → район (architecture.md §3).

Мультирегиональность заложена с 1-го дня (CLAUDE.md, принцип 6). Названия —
ru/uz (конвенция бренда). Район привязывается к точке прокатчика (supplier.district_id)
и наследуется карточкой; сами таблицы — справочные, наполняются из админки/сидов.
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_ru: Mapped[str] = mapped_column(String(100))
    name_uz: Mapped[str] = mapped_column(String(100))

    cities: Mapped[list["City"]] = relationship(
        back_populates="region", cascade="all, delete-orphan"
    )


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id", ondelete="CASCADE"), index=True)
    name_ru: Mapped[str] = mapped_column(String(100))
    name_uz: Mapped[str] = mapped_column(String(100))

    region: Mapped["Region"] = relationship(back_populates="cities")
    districts: Mapped[list["District"]] = relationship(
        back_populates="city", cascade="all, delete-orphan"
    )


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), index=True)
    name_ru: Mapped[str] = mapped_column(String(100))
    name_uz: Mapped[str] = mapped_column(String(100))

    city: Mapped["City"] = relationship(back_populates="districts")
