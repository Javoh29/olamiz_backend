"""Единая точка импорта ORM-моделей — для Alembic autogenerate.

Каждый новый модуль `domain/<name>/models.py` ДОЛЖЕН быть импортирован здесь,
иначе его таблицы не попадут в `Base.metadata` и не увидятся автогенерацией миграций.
"""

from app.domain.geo import models as geo  # noqa: F401
from app.domain.suppliers import models as suppliers  # noqa: F401
from app.domain.users import models as users  # noqa: F401
