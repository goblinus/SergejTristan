"""Дивидендные метрики: доходность к текущей цене и DSI (ADR-0005)."""

from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from app.schemas.dividend import DividendTerms

if TYPE_CHECKING:
    from app.models.shareholder_meeting import ShareholderMeeting
    from app.models.ticker import Ticker

# Горизонт DSI: последние 5 завершённых календарных лет.
DSI_HORIZON_YEARS = 5
# Минимум лет с выплатами, иначе DSI не определён.
DSI_MIN_PAYMENT_YEARS = 3


def compute_yield(amount_per_share: Decimal | None, last_price: Decimal | None) -> float | None:
    """Доходность к текущей цене, %: amount / price * 100 с округлением до 0.1.

    Возвращает None, если сумма или цена отсутствуют либо цена неположительна.
    Сумма 0 допустима (CHECK >= 0) и даёт доходность 0.0.
    """
    if amount_per_share is None or last_price is None:
        return None
    if last_price <= 0:
        return None
    return round(float(amount_per_share) / float(last_price) * 100, 1)


def build_dividend_terms(
    meeting: "ShareholderMeeting", ticker: "Ticker"
) -> DividendTerms | None:
    """Собирает дивидендные условия собрания; None, если не известны ни период, ни сумма."""
    if meeting.dividend_period is None and meeting.dividend_per_share is None:
        return None

    amount = meeting.dividend_per_share
    return DividendTerms(
        period=meeting.dividend_period,  # type: ignore[arg-type]
        amount_per_share=float(amount) if amount is not None else None,
        yield_percent=compute_yield(amount, ticker.last_price),
    )


def get_dsi(ticker: "Ticker") -> int | None:
    """DSI эмитента: материализованный снапшот, на чтении не пересчитывается."""
    return ticker.dsi


def _to_decimal(value: Decimal | int | float) -> Decimal:
    """Приводит значение к Decimal без потери точности для float-входа."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    return Decimal(str(value))


def calc_dsi(yearly_dps: list[Decimal]) -> int | None:
    """DSI по годовым суммам выплат на акцию (формула ADR-0005).

    Горизонт — последние 5 лет; годы без выплат дают DPS = 0.
    None, если лет с выплатами меньше 3.
    """
    if not yearly_dps:
        return None

    values = [_to_decimal(v) for v in yearly_dps][-DSI_HORIZON_YEARS:]
    if len(values) < DSI_HORIZON_YEARS:
        values = [Decimal(0)] * (DSI_HORIZON_YEARS - len(values)) + values

    payment_years = sum(1 for v in values if v > 0)
    if payment_years < DSI_MIN_PAYMENT_YEARS:
        # Исключение: полный горизонт без выплат — история есть, все DPS нулевые
        # (спецификация §3.3): считается низкий DSI, а не null.
        all_zero_full_horizon = payment_years == 0 and len(yearly_dps) >= DSI_HORIZON_YEARS
        if not all_zero_full_horizon:
            return None

    horizon = Decimal(len(values))
    regularity = Decimal(payment_years) / horizon

    mean = sum(values, Decimal(0)) / horizon
    if mean == 0:
        stability = Decimal(0)
    else:
        variance = sum(((v - mean) ** 2 for v in values), Decimal(0)) / horizon
        std_dev = variance.sqrt()
        stability = Decimal(1) - min(Decimal(1), std_dev / mean)

    transitions = len(values) - 1
    no_decrease = sum(1 for prev, cur in zip(values, values[1:], strict=False) if cur >= prev)
    stability_ratio = Decimal(no_decrease) / Decimal(transitions) if transitions else Decimal(0)

    score = Decimal(100) * (
        Decimal("0.4") * regularity + Decimal("0.4") * stability + Decimal("0.2") * stability_ratio
    )
    return int(score.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
