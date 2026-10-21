"""ORM-модель собрания акционеров."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.record_date import RecordDate
    from app.models.ticker import Ticker


class ShareholderMeeting(Base):
    """Собрание акционеров с вопросом о дивидендах."""

    __tablename__ = "shareholder_meetings"
    __table_args__ = (
        UniqueConstraint(
            "ticker_id", "meeting_date", "meeting_type", name="uq_meetings_business_key"
        ),
        CheckConstraint(
            "dividend_per_share IS NULL OR dividend_per_share >= 0",
            name="ck_meetings_dividend_per_share_non_negative",
        ),
        Index("ix_meetings_date", "meeting_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id", ondelete="RESTRICT"), nullable=False
    )
    meeting_date: Mapped[date] = mapped_column(Date, nullable=False)
    meeting_type: Mapped[str] = mapped_column(String(16), nullable=False)
    dividend_question: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dividend_period: Mapped[str | None] = mapped_column(String(16), nullable=True)
    dividend_per_share: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ticker: Mapped["Ticker"] = relationship(back_populates="meetings")
    record_dates: Mapped[list["RecordDate"]] = relationship(
        back_populates="meeting",
        passive_deletes=True,
    )
