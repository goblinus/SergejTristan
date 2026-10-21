"""Pydantic-схемы (DTO) API."""

from app.schemas.common import ErrorResponse, Page
from app.schemas.dividend import DividendTerms
from app.schemas.meeting import Meeting
from app.schemas.record_date import RecordDate, RecordDateBrief
from app.schemas.ticker import Ticker
from app.schemas.watchlist import WatchlistCreate, WatchlistItem, WatchStatus

__all__ = [
    "DividendTerms",
    "ErrorResponse",
    "Meeting",
    "Page",
    "RecordDate",
    "RecordDateBrief",
    "Ticker",
    "WatchStatus",
    "WatchlistCreate",
    "WatchlistItem",
]
