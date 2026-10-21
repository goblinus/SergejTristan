"""ORM-модели; импорт всех моделей регистрирует их в Base.metadata."""

from app.models.base import Base
from app.models.record_date import RecordDate
from app.models.shareholder_meeting import ShareholderMeeting
from app.models.ticker import Ticker
from app.models.watchlist_item import WatchlistItem

__all__ = ["Base", "RecordDate", "ShareholderMeeting", "Ticker", "WatchlistItem"]
