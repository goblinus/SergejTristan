"""Репозиторий дат отсечки."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.record_date import RecordDate
from app.models.ticker import Ticker


@dataclass(frozen=True, slots=True)
class RecordDateUpsert:
    """Данные отсечки для идемпотентного upsert из скриптов сбора."""

    ticker_id: int
    meeting_id: int | None
    record_date: date
    kind: str
    source_url: str
    fetched_at: datetime


def _record_dates_query(
    date_from: date, date_to: date, ticker: str | None, kind: str
) -> Select:
    """Базовый запрос календаря отсечек."""
    stmt = (
        select(RecordDate)
        .join(RecordDate.ticker)
        .where(
            RecordDate.record_date >= date_from,
            RecordDate.record_date <= date_to,
            RecordDate.kind == kind,
        )
    )
    if ticker is not None:
        stmt = stmt.where(Ticker.ticker == ticker)
    return stmt


def list_record_dates(
    session: Session,
    date_from: date,
    date_to: date,
    ticker: str | None = None,
    kind: str = "dividend_payment",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[RecordDate], int]:
    """Даты отсечки в [date_from, date_to], record_date ASC."""
    stmt = _record_dates_query(date_from, date_to, ticker, kind)
    total = session.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()

    rows = list(
        session.execute(
            stmt.options(selectinload(RecordDate.ticker))
            .order_by(RecordDate.record_date.asc(), RecordDate.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars()
    )
    return rows, total


def get_next_for_ticker(
    session: Session, ticker_id: int, today: date
) -> RecordDate | None:
    """Ближайшая отсечка kind = dividend_payment с record_date >= today."""
    return session.execute(
        select(RecordDate)
        .where(
            RecordDate.ticker_id == ticker_id,
            RecordDate.kind == "dividend_payment",
            RecordDate.record_date >= today,
        )
        .order_by(RecordDate.record_date.asc())
        .limit(1)
    ).scalar_one_or_none()


def upsert_record_dates(
    session: Session, items: Iterable[RecordDateUpsert]
) -> tuple[int, int]:
    """Идемпотентный upsert по бизнес-ключу (ticker_id, record_date, kind).

    Возвращает (вставлено, обновлено). Существующая связь с собранием
    не сбрасывается, если новая запись не содержит ссылки на собрание.
    """
    by_key = {(item.ticker_id, item.record_date, item.kind): item for item in items}
    if not by_key:
        return 0, 0

    existing = {
        (row.ticker_id, row.record_date, row.kind): row
        for row in session.execute(
            select(RecordDate).where(RecordDate.ticker_id.in_({key[0] for key in by_key}))
        ).scalars()
    }

    inserted = 0
    updated = 0

    for key, item in by_key.items():
        row = existing.get(key)
        if row is None:
            session.add(
                RecordDate(
                    ticker_id=item.ticker_id,
                    meeting_id=item.meeting_id,
                    record_date=item.record_date,
                    kind=item.kind,
                    source_url=item.source_url,
                    fetched_at=item.fetched_at,
                )
            )
            inserted += 1
        else:
            if item.meeting_id is not None:
                row.meeting_id = item.meeting_id
            row.source_url = item.source_url
            row.fetched_at = item.fetched_at
            updated += 1

    session.flush()
    return inserted, updated
