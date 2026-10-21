"""ORM-модель «сторожка» пользователя."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ticker import Ticker


class WatchlistItem(Base):
    """Отслеживаемый тикер; одна строка на тикер (однопользовательская система)."""

    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("ticker_id", name="uq_watchlist_ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id", ondelete="RESTRICT"), nullable=False
    )
    threshold_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ticker: Mapped["Ticker"] = relationship(back_populates="watchlist_item")
