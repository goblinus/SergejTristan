"""Репозиторий дат отсечки."""

from datetime import date

from sqlalchemy.orm import Session

from app.models.record_date import RecordDate


def list_record_dates(
    session: Session,
    date_from: date,
    date_to: date,
    ticker: str | None = None,
    kind: str = "dividend_payment",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[RecordDate], int]:
    """Даты отсечки в [date_from, date_to], record_date ASC.

    TODO: реализовать join с tickers (для DTO), фильтры ticker/kind, offset/limit и count.
    Пока — пустой результат для каркаса API.
    """
    return [], 0


def get_next_for_ticker(
    session: Session, ticker_id: int, today: date
) -> RecordDate | None:
    """Ближайшая отсечка kind = dividend_payment с record_date >= today.

    TODO: реализовать выборку минимальной даты (нужна для статусов сторожков).
    """
    return None
