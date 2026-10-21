"""Pydantic-схемы «сторожка»."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import UtcDatetime
from app.schemas.dividend import DividendTerms

WatchStatus = Literal["no_date", "far", "near", "hot", "critical", "past"]


class WatchlistItem(BaseModel):
    """Сторожок с вычисленными на чтении полями."""

    ticker: str
    short_name: str
    logo_url: str | None = None
    threshold_days: int
    created_at: UtcDatetime
    next_record_date: date | None = None
    next_meeting_date: date | None = None
    days_to_cutoff: int | None = None
    status: WatchStatus
    next_dividend: DividendTerms | None = None
    dsi: int | None = Field(default=None, ge=0, le=100)


class WatchlistCreate(BaseModel):
    """Тело POST /watchlist."""

    ticker: str
    threshold_days: int | None = Field(default=None, ge=1, le=365)

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        """Нормализует тикер: trim и верхний регистр."""
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("ticker must not be empty")
        return normalized
