"""Ранжирование выдачи каталога — единственная формула (architecture.md §7).

    score = w1·speed + w2·rating + w3·completeness − w4·cancel_rate

Каждый под-скор нормирован в [0, 1]; веса — из конфига (rank_w1..w4), тюнятся по данным.
Новичок без истории получает нейтральные 0.5 — не топим и не поднимаем.
Формула живёт здесь и только здесь; менять — вместе с тестами.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from app.domain.catalog.models import Listing

# Опорные точки нормировки скорости ответа прокатчика.
FAST_RESPONSE_SEC = 5 * 60  # ≤5 мин — максимум скорости
SLOW_RESPONSE_SEC = 60 * 60  # ≥1 час — минимум
NEUTRAL = 0.5  # нет истории → нейтрально, ни вверх ни вниз

# Рейтинги в БД — по шкале 1..5.
RATING_MIN = 1.0
RATING_MAX = 5.0

# Полнота карточки: фото весомее описания.
FULL_PHOTO_COUNT = 3  # столько фото считаем «полным» комплектом
PHOTO_WEIGHT = 0.7
DESCRIPTION_WEIGHT = 0.3


@dataclass(frozen=True)
class RankWeights:
    """Веса формулы (из settings.rank_w1..w4)."""

    w1: float
    w2: float
    w3: float
    w4: float


@dataclass(frozen=True)
class RankingSignals:
    """Сырые сигналы карточки+прокатчика, расцепленные с ORM (тестируется без БД)."""

    response_median_sec: int | None
    supplier_rating: Decimal | None
    listing_rating: Decimal | None
    photo_count: int
    has_description: bool
    cancel_rate: float  # доля отмен прокатчиком в [0, 1]; новичок → 0.0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def response_speed_score(median_sec: int | None) -> float:
    """Быстрее отвечает — выше. Линейно между опорными точками; нет истории → нейтрально."""
    if median_sec is None:
        return NEUTRAL
    if median_sec <= FAST_RESPONSE_SEC:
        return 1.0
    if median_sec >= SLOW_RESPONSE_SEC:
        return 0.0
    span = SLOW_RESPONSE_SEC - FAST_RESPONSE_SEC
    return 1.0 - (median_sec - FAST_RESPONSE_SEC) / span


def rating_score(supplier_rating: Decimal | None, listing_rating: Decimal | None) -> float:
    """Среднее из доступных рейтингов (1..5) → [0, 1]; ни одного → нейтрально."""
    present = [float(r) for r in (supplier_rating, listing_rating) if r is not None]
    if not present:
        return NEUTRAL
    avg = sum(present) / len(present)
    return _clamp01((avg - RATING_MIN) / (RATING_MAX - RATING_MIN))


def completeness_score(photo_count: int, has_description: bool) -> float:
    """Качество карточки: доля фото до «полного» комплекта + наличие описания."""
    photo_part = _clamp01(photo_count / FULL_PHOTO_COUNT)
    desc_part = 1.0 if has_description else 0.0
    return _clamp01(PHOTO_WEIGHT * photo_part + DESCRIPTION_WEIGHT * desc_part)


def score(signals: RankingSignals, weights: RankWeights) -> float:
    """Итоговый score карточки. Веса передаются явно — модуль не лезет в глобальный конфиг."""
    return (
        weights.w1 * response_speed_score(signals.response_median_sec)
        + weights.w2 * rating_score(signals.supplier_rating, signals.listing_rating)
        + weights.w3 * completeness_score(signals.photo_count, signals.has_description)
        - weights.w4 * _clamp01(signals.cancel_rate)
    )


def weights_from_settings(settings: Settings | None = None) -> RankWeights:
    s = settings or get_settings()
    return RankWeights(w1=s.rank_w1, w2=s.rank_w2, w3=s.rank_w3, w4=s.rank_w4)


def signals_from_listing(listing: Listing) -> RankingSignals:
    """Собрать сигналы из ORM-карточки (нужны загруженные supplier и photos)."""
    supplier = listing.supplier
    return RankingSignals(
        response_median_sec=supplier.response_median_sec,
        supplier_rating=supplier.rating,
        listing_rating=listing.rating,
        photo_count=len(listing.photos),
        has_description=bool(listing.description and listing.description.strip()),
        # Счётчик отмен прокатчиком появится с booking/worker; пока нейтрально.
        cancel_rate=0.0,
    )
