"""Pydantic-схемы тикера."""

from pydantic import BaseModel

from app.schemas.common import UtcDatetime


class Ticker(BaseModel):
    """Тикер в ответах API (source_url наружу не отдаётся)."""

    ticker: str
    short_name: str
    full_name: str | None = None
    isin: str | None = None
    board: str | None = None
    lot_size: int | None = None
    logo_url: str | None = None
    is_active: bool
    fetched_at: UtcDatetime
