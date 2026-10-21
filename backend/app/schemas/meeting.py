"""Pydantic-схемы собрания акционеров."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import UtcDatetime
from app.schemas.dividend import DividendTerms
from app.schemas.record_date import RecordDateBrief

MeetingType = Literal["annual", "extraordinary"]


class Meeting(BaseModel):
    """Собрание акционеров в ответах API."""

    id: int
    ticker: str
    short_name: str
    logo_url: str | None = None
    meeting_date: date
    meeting_type: MeetingType
    description: str | None = None
    dividend: DividendTerms | None = None
    dsi: int | None = Field(default=None, ge=0, le=100)
    source_url: str
    fetched_at: UtcDatetime
    record_date: RecordDateBrief | None = None
