"""ORM-модели каталога: категории (architecture.md §3, product-spec §5).

Дерево категорий создаёт и контролирует платформа (D11): прокатчик их не создаёт.
До 3 уровней (в MVP используется 2). Названия — ru/uz, slug уникален (SEO-URL витрины).
Карточки (listing), units — отдельным инкрементом.
"""

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


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
