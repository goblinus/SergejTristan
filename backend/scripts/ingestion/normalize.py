"""Нормализация разобранных фактов в канонические DTO (вне API-схем)."""

import logging
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from scripts.ingestion.parsers.moex_tickers import MoexSecurity

logger = logging.getLogger(__name__)

MeetingType = Literal["annual", "extraordinary"]
DividendPeriod = Literal["year", "half_year", "quarter"]
RecordDateKind = Literal["dividend_payment", "meeting_participation"]


class NormalizedTicker(BaseModel):
    """Канонический тикер после нормализации."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticker: str = Field(min_length=1)
    short_name: str = Field(min_length=1)
    full_name: str | None = None
    isin: str | None = None
    board: str | None = None
    lot_size: int | None = None
    last_price: Decimal | None = Field(default=None, gt=0)
    source_url: str
    fetched_at: datetime

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        """SECID хранится в верхнем регистре без пробелов."""
        return value.strip().upper()


class NormalizedMeeting(BaseModel):
    """Каноническое собрание акционеров с вопросом о дивидендах."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticker: str
    meeting_date: date
    meeting_type: MeetingType
    dividend_question: bool = True
    dividend_period: DividendPeriod | None = None
    dividend_per_share: Decimal | None = Field(default=None, ge=0)
    description: str | None = None
    source_url: str
    fetched_at: datetime

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class NormalizedRecordDate(BaseModel):
    """Каноническая дата закрытия реестра."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticker: str
    record_date: date
    kind: RecordDateKind = "dividend_payment"
    meeting_id: int | None = None
    source_url: str
    fetched_at: datetime

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class NormalizedDividendMetrics(BaseModel):
    """DSI эмитента — материализованный снапшот (ADR-0005)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticker: str
    dsi: int | None = Field(default=None, ge=0, le=100)
    dsi_updated_at: datetime

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


def normalize_tickers(
    facts: Iterable[MoexSecurity], *, source_url: str, fetched_at: datetime
) -> list[NormalizedTicker]:
    """Приводит факты MOEX ISS к каноническим DTO и дедуплицирует по тикеру.

    Некорректная запись отбрасывается с WARNING, остальные обрабатываются.
    """
    result: dict[str, NormalizedTicker] = {}

    for fact in facts:
        try:
            item = NormalizedTicker(
                ticker=fact.secid,
                short_name=fact.short_name,
                full_name=fact.full_name,
                isin=fact.isin,
                board=fact.board,
                lot_size=fact.lot_size,
                last_price=fact.last_price,
                source_url=source_url,
                fetched_at=fetched_at,
            )
        except ValidationError as exc:
            logger.warning("skip ticker=%r: %s", fact.secid, exc.errors())
            continue
        result[item.ticker] = item

    return list(result.values())
