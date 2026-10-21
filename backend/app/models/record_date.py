"""ORM-модель даты закрытия реестра (отсечки)."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.shareholder_meeting import ShareholderMeeting
    from app.models.ticker import Ticker


class RecordDate(Base):
    """Дата отсечки: для выплаты дивидендов или для участия в собрании."""

    __tablename__ = "record_dates"
    __table_args__ = (
        UniqueConstraint("ticker_id", "record_date", "kind", name="uq_record_dates_business_key"),
        Index("ix_record_dates_date", "record_date"),
        Index("ix_record_dates_ticker_kind", "ticker_id", "kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id", ondelete="RESTRICT"), nullable=False
    )
    meeting_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("shareholder_meetings.id", ondelete="SET NULL"), nullable=True
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="dividend_payment")
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ticker: Mapped["Ticker"] = relationship(back_populates="record_dates")
    meeting: Mapped[Optional["ShareholderMeeting"]] = relationship(back_populates="record_dates")
