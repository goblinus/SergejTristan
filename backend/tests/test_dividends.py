"""Юнит-тесты дивидендной доходности и DSI."""

from decimal import Decimal

import pytest

from app.services.dividends import calc_dsi, compute_yield


@pytest.mark.parametrize(
    ("amount", "price", "expected"),
    [
        (Decimal("33.30"), Decimal("396.40"), 8.4),
        (Decimal("26.00"), Decimal("333.00"), 7.8),
        (Decimal("1"), Decimal("3"), 33.3),
        (None, Decimal("100"), None),
        (Decimal("10"), None, None),
        (Decimal("10"), Decimal("0"), None),
        (Decimal("10"), Decimal("-1"), None),
        (Decimal("0"), Decimal("100"), 0.0),
    ],
)
def test_compute_yield(amount, price, expected) -> None:
    """Доходность к текущей цене с округлением до 0.1 и None-кейсами."""
    assert compute_yield(amount, price) == expected


def test_compute_yield_rounding() -> None:
    """Округление до одного знака после запятой."""
    assert compute_yield(Decimal("10"), Decimal("7")) == round(10 / 7 * 100, 1)


def test_dsi_spec_example() -> None:
    """Пример из спецификации: DPS 10, 12, 12, 14, 15 -> 94."""
    dps = [Decimal("10"), Decimal("12"), Decimal("12"), Decimal("14"), Decimal("15")]
    assert calc_dsi(dps) == 94


def test_dsi_stable_payments() -> None:
    """Ровные выплаты: R = S = N = 1 -> 100."""
    assert calc_dsi([Decimal("10")] * 5) == 100


def test_dsi_all_zero() -> None:
    """Нулевые выплаты: R = 0, S = 0, N = 1 -> 20."""
    assert calc_dsi([Decimal("0")] * 5) == 20


def test_dsi_declining_payments() -> None:
    """Снижение выплат каждый год: N = 0, DSI ниже 100."""
    dps = [Decimal("15"), Decimal("14"), Decimal("13"), Decimal("12"), Decimal("10")]
    assert calc_dsi(dps) == 75


def test_dsi_with_gaps() -> None:
    """Годы без выплат дают DPS = 0 и снижают регулярность."""
    dps = [Decimal("10"), Decimal("0"), Decimal("12"), Decimal("0"), Decimal("14")]
    assert calc_dsi(dps) == 41


def test_dsi_less_than_three_payment_years() -> None:
    """Меньше 3 лет с выплатами — DSI не определён."""
    assert calc_dsi([Decimal("10"), Decimal("12")]) is None
    assert calc_dsi([Decimal("10"), Decimal("0"), Decimal("0")]) is None
    assert calc_dsi([]) is None


def test_dsi_accepts_int_input() -> None:
    """Функция принимает целые значения годовых DPS."""
    assert calc_dsi([10, 12, 12, 14, 15]) == 94
