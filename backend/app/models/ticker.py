"""ORM-модель тикера Московской биржи."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.record_date import RecordDate
    from app.models.shareholder_meeting import ShareholderMeeting
    from app.models.watchlist_item import WatchlistItem


class Ticker(Base):
    """Тикер (SECID MOEX) с метриками эмитента."""

    __tablename__ = "tickers"
    __table_args__ = (
        UniqueConstraint("ticker", name="uq_tickers_ticker"),
        CheckConstraint("dsi IS NULL OR (dsi >= 0 AND dsi <= 100)", name="ck_tickers_dsi_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    short_name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    board: Mapped[str | None] = mapped_column(String(16), nullable=True)
    lot_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    price_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dsi: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    dsi_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    meetings: Mapped[list["ShareholderMeeting"]] = relationship(
        back_populates="ticker",
        cascade="save-update, merge",
        passive_deletes=True,
    )
    record_dates: Mapped[list["RecordDate"]] = relationship(
        back_populates="ticker",
        cascade="save-update, merge",
        passive_deletes=True,
    )
    watchlist_item: Mapped[Optional["WatchlistItem"]] = relationship(
        back_populates="ticker",
        uselist=False,
        passive_deletes=True,
    )
