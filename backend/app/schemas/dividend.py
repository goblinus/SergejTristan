"""Pydantic-схемы дивидендных метрик."""

from typing import Literal

from pydantic import BaseModel, Field

DividendPeriod = Literal["year", "half_year", "quarter"]


class DividendTerms(BaseModel):
    """Дивидендные условия: период, сумма на акцию, доходность к текущей цене."""

    period: DividendPeriod | None = None
    amount_per_share: float | None = Field(default=None, ge=0)
    yield_percent: float | None = Field(default=None, ge=0)
