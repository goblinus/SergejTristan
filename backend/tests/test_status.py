"""Юнит-тесты статуса сторожка по таблице примеров спецификации."""

from datetime import date

import pytest

from app.services.watchlist import calc_days_to_cutoff, calc_status

TODAY = date(2026, 10, 19)
THRESHOLD = 7
SOON = 14


@pytest.mark.parametrize(
    ("next_record_date", "expected"),
    [
        (date(2026, 10, 19), "critical"),
        (date(2026, 10, 25), "hot"),
        (date(2026, 10, 26), "hot"),
        (date(2026, 10, 27), "near"),
        (date(2026, 11, 2), "near"),
        (date(2026, 11, 3), "far"),
    ],
)
def test_status_with_next_date(next_record_date: date, expected: str) -> None:
    """Границы зон critical/hot/near/far."""
    assert calc_status(TODAY, THRESHOLD, SOON, next_record_date, has_past_dates=False) == expected


def test_status_past_when_no_future_dates() -> None:
    """Будущих дат нет, прошедшие есть — past."""
    assert calc_status(TODAY, THRESHOLD, SOON, None, has_past_dates=True) == "past"


def test_status_no_date_when_no_records() -> None:
    """Записей dividend_payment нет — no_date."""
    assert calc_status(TODAY, THRESHOLD, SOON, None, has_past_dates=False) == "no_date"


def test_status_threshold_beyond_soon_days() -> None:
    """При T >= S граница near схлопывается, hot получает приоритет."""
    assert calc_status(TODAY, 14, 14, date(2026, 10, 29), has_past_dates=False) == "hot"
    assert calc_status(TODAY, 30, 14, date(2026, 10, 29), has_past_dates=False) == "hot"


def test_days_to_cutoff() -> None:
    """Число суток до отсечки; None без даты."""
    assert calc_days_to_cutoff(TODAY, date(2026, 10, 22)) == 3
    assert calc_days_to_cutoff(TODAY, TODAY) == 0
    assert calc_days_to_cutoff(TODAY, None) is None
