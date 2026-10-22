"""Сервис календаря: собрания акционеров и даты отсечки."""

from datetime import date

from sqlalchemy.orm import Session

from app.repositories import meetings as meetings_repo
from app.repositories import record_dates as record_dates_repo
from app.schemas.common import Page
from app.schemas.meeting import Meeting
from app.schemas.record_date import RecordDate, RecordDateBrief, RecordDateKind
from app.services.dividends import build_dividend_terms, get_dsi


def _select_dividend_record_date(meeting):
    """Выбирает отсечку dividend_payment, вложенную в карточку собрания.

    Если связанных отсечек несколько, предпочитается ближайшая на дату
    собрания или позже; иначе — самая поздняя из имеющихся.
    """
    candidates = [rd for rd in meeting.record_dates if rd.kind == "dividend_payment"]
    if not candidates:
        return None

    after = [rd for rd in candidates if rd.record_date >= meeting.meeting_date]
    if after:
        return min(after, key=lambda rd: rd.record_date)
    return max(candidates, key=lambda rd: rd.record_date)


def meeting_to_dto(meeting) -> Meeting:
    """Собирает DTO собрания с дивидендными условиями и вложенной отсечкой."""
    ticker = meeting.ticker
    record_date = _select_dividend_record_date(meeting)
    return Meeting(
        id=meeting.id,
        ticker=ticker.ticker,
        short_name=ticker.short_name,
        logo_url=ticker.logo_url,
        meeting_date=meeting.meeting_date,
        meeting_type=meeting.meeting_type,
        description=meeting.description,
        dividend=build_dividend_terms(meeting, ticker),
        dsi=get_dsi(ticker),
        source_url=meeting.source_url,
        fetched_at=meeting.fetched_at,
        record_date=(
            RecordDateBrief(
                record_date=record_date.record_date,
                kind=record_date.kind,
                fetched_at=record_date.fetched_at,
            )
            if record_date is not None
            else None
        ),
    )


def record_date_to_dto(record_date) -> RecordDate:
    """Собирает DTO даты отсечки."""
    return RecordDate(
        ticker=record_date.ticker.ticker,
        record_date=record_date.record_date,
        kind=record_date.kind,
        meeting_id=record_date.meeting_id,
        fetched_at=record_date.fetched_at,
    )


def list_meetings(
    session: Session,
    date_from: date,
    date_to: date,
    ticker: str | None,
    page: int,
    page_size: int,
) -> Page[Meeting]:
    """Собрания с вопросом о дивидендах в интервале [from, to]."""
    rows, total = meetings_repo.list_meetings(
        session, date_from=date_from, date_to=date_to, ticker=ticker, page=page, page_size=page_size
    )
    return Page(
        items=[meeting_to_dto(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def get_meeting(session: Session, meeting_id: int) -> Meeting | None:
    """Карточка собрания по id; None, если не найдено."""
    row = meetings_repo.get_meeting(session, meeting_id)
    return None if row is None else meeting_to_dto(row)


def list_record_dates(
    session: Session,
    date_from: date,
    date_to: date,
    ticker: str | None,
    kind: RecordDateKind,
    page: int,
    page_size: int,
) -> Page[RecordDate]:
    """Даты отсечки в интервале [from, to]."""
    rows, total = record_dates_repo.list_record_dates(
        session,
        date_from=date_from,
        date_to=date_to,
        ticker=ticker,
        kind=kind,
        page=page,
        page_size=page_size,
    )
    return Page(
        items=[record_date_to_dto(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
