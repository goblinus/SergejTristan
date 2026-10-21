"""Pydantic-схемы дат отсечки."""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.schemas.common import UtcDatetime

RecordDateKind = Literal["dividend_payment", "meeting_participation"]


class RecordDate(BaseModel):
    """Дата отсечки в ответах API."""

    ticker: str
    record_date: date
    kind: RecordDateKind
    meeting_id: int | None = None
    fetched_at: UtcDatetime


class RecordDateBrief(BaseModel):
    """Вложенная отсечка в карточке собрания."""

    record_date: date
    kind: RecordDateKind
    fetched_at: UtcDatetime
