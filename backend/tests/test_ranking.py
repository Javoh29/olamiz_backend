"""Формула ранжирования каталога (architecture.md §7) — чистые тесты, без БД."""

from decimal import Decimal

import pytest

from app.domain.catalog import ranking
from app.domain.catalog.ranking import RankingSignals, RankWeights

WEIGHTS = RankWeights(w1=0.3, w2=0.3, w3=0.2, w4=0.2)


def _signals(**overrides: object) -> RankingSignals:
    base: dict[str, object] = {
        "response_median_sec": None,
        "supplier_rating": None,
        "listing_rating": None,
        "photo_count": 0,
        "has_description": False,
        "cancel_rate": 0.0,
    }
    base.update(overrides)
    return RankingSignals(**base)  # type: ignore[arg-type]


# --- под-скор: скорость ответа ---


def test_speed_neutral_when_no_history() -> None:
    assert ranking.response_speed_score(None) == ranking.NEUTRAL


def test_speed_fast_is_max() -> None:
    assert ranking.response_speed_score(ranking.FAST_RESPONSE_SEC) == 1.0
    assert ranking.response_speed_score(10) == 1.0


def test_speed_slow_is_min() -> None:
    assert ranking.response_speed_score(ranking.SLOW_RESPONSE_SEC) == 0.0
    assert ranking.response_speed_score(10 * 3600) == 0.0


def test_speed_monotonic_in_between() -> None:
    mid = (ranking.FAST_RESPONSE_SEC + ranking.SLOW_RESPONSE_SEC) // 2
    assert ranking.response_speed_score(mid) == pytest.approx(0.5, abs=0.02)


# --- под-скор: рейтинг ---


def test_rating_neutral_when_absent() -> None:
    assert ranking.rating_score(None, None) == ranking.NEUTRAL


def test_rating_top_and_bottom() -> None:
    assert ranking.rating_score(Decimal("5.0"), Decimal("5.0")) == 1.0
    assert ranking.rating_score(Decimal("1.0"), Decimal("1.0")) == 0.0


def test_rating_averages_present_values() -> None:
    # доступен только рейтинг карточки = 3.0 → (3-1)/4 = 0.5
    assert ranking.rating_score(None, Decimal("3.0")) == pytest.approx(0.5)


# --- под-скор: полнота карточки ---


def test_completeness_empty_is_zero() -> None:
    assert ranking.completeness_score(0, has_description=False) == 0.0


def test_completeness_full_is_one() -> None:
    assert ranking.completeness_score(3, has_description=True) == pytest.approx(1.0)
    assert ranking.completeness_score(10, has_description=True) == pytest.approx(1.0)


def test_completeness_photos_weigh_more_than_description() -> None:
    only_photos = ranking.completeness_score(3, has_description=False)
    only_desc = ranking.completeness_score(0, has_description=True)
    assert only_photos > only_desc


# --- итоговая формула ---


def test_loaded_listing_outranks_bare_newbie() -> None:
    loaded = _signals(
        response_median_sec=60,
        supplier_rating=Decimal("4.8"),
        listing_rating=Decimal("4.9"),
        photo_count=4,
        has_description=True,
    )
    newbie = _signals()  # всё пусто → нейтрально
    assert ranking.score(loaded, WEIGHTS) > ranking.score(newbie, WEIGHTS)


def test_cancellations_pull_score_down() -> None:
    clean = _signals(supplier_rating=Decimal("4.5"), photo_count=3, has_description=True)
    cancels = _signals(
        supplier_rating=Decimal("4.5"),
        photo_count=3,
        has_description=True,
        cancel_rate=1.0,
    )
    assert ranking.score(cancels, WEIGHTS) < ranking.score(clean, WEIGHTS)


def test_neutral_newbie_score_is_stable() -> None:
    # Новичок: speed=rating=0.5, completeness=0, cancel=0 → 0.3*0.5 + 0.3*0.5 + 0 - 0 = 0.3
    assert ranking.score(_signals(), WEIGHTS) == pytest.approx(0.3)


def test_weights_from_settings_reads_config() -> None:
    weights = ranking.weights_from_settings()
    assert (weights.w1, weights.w2, weights.w3, weights.w4) == (0.3, 0.3, 0.2, 0.2)
