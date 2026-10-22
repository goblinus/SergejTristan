"""Репозиторий «сторожков»."""

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.record_date import RecordDate
from app.models.shareholder_meeting import ShareholderMeeting
from app.models.ticker import Ticker
from app.models.watchlist_item import WatchlistItem


def list_items(session: Session) -> list[WatchlistItem]:
    """Все сторожки с загруженным тикером.

    Список одного пользователя невелик (десятки записей), поэтому выборка
    выполняется целиком: сортировка требует вычисленного статуса, который
    зависит от `threshold_days` и текущей даты.
    """
    return list(
        session.execute(
            select(WatchlistItem)
            .options(selectinload(WatchlistItem.ticker))
            .order_by(WatchlistItem.id.asc())
        ).scalars()
    )


def get_by_ticker(session: Session, ticker: str) -> WatchlistItem | None:
    """Сторожок по SECID тикера (верхний регистр)."""
    return session.execute(
        select(WatchlistItem)
        .join(WatchlistItem.ticker)
        .where(Ticker.ticker == ticker)
        .options(selectinload(WatchlistItem.ticker))
    ).scalar_one_or_none()


def get_next_record_dates(
    session: Session, ticker_ids: set[int], today: date
) -> dict[int, RecordDate]:
    """Ближайшие отсечки dividend_payment с record_date >= today по тикерам.

    Возвращает отображение ticker_id -> отсечка. Связанное собрание
    загружается eager-загрузкой для расчёта `next_meeting_date` и
    `next_dividend` без N+1.
    """
    if not ticker_ids:
        return {}

    rows = session.execute(
        select(RecordDate)
        .where(
            RecordDate.ticker_id.in_(ticker_ids),
            RecordDate.kind == "dividend_payment",
            RecordDate.record_date >= today,
        )
        .options(selectinload(RecordDate.meeting))
        .order_by(RecordDate.ticker_id.asc(), RecordDate.record_date.asc(), RecordDate.id.asc())
    ).scalars()

    next_dates: dict[int, RecordDate] = {}
    for row in rows:
        next_dates.setdefault(row.ticker_id, row)
    return next_dates


def get_next_meetings(
    session: Session, ticker_ids: set[int], today: date
) -> dict[int, ShareholderMeeting]:
    """Ближайшие будущие собрания с дивидендным вопросом по тикерам.

    Возвращает отображение ticker_id -> собрание (минимальная `meeting_date`
    при `meeting_date >= today`). Используется как fallback-событие сторожка,
    когда будущей отсечки `dividend_payment` нет.
    """
    if not ticker_ids:
        return {}

    rows = session.execute(
        select(ShareholderMeeting)
        .where(
            ShareholderMeeting.ticker_id.in_(ticker_ids),
            ShareholderMeeting.dividend_question.is_(True),
            ShareholderMeeting.meeting_date >= today,
        )
        .order_by(
            ShareholderMeeting.ticker_id.asc(),
            ShareholderMeeting.meeting_date.asc(),
            ShareholderMeeting.id.asc(),
        )
    ).scalars()

    next_meetings: dict[int, ShareholderMeeting] = {}
    for row in rows:
        next_meetings.setdefault(row.ticker_id, row)
    return next_meetings


def get_ticker_ids_with_past_events(
    session: Session, ticker_ids: set[int], today: date
) -> set[int]:
    """Тикеры с прошедшими дивидендными событиями.

    Учитываются прошедшие отсечки `dividend_payment` (record_date < today) и
    прошедшие собрания с `dividend_question = true` (meeting_date < today).
    """
    if not ticker_ids:
        return set()

    past_record_dates = set(
        session.execute(
            select(RecordDate.ticker_id)
            .where(
                RecordDate.ticker_id.in_(ticker_ids),
                RecordDate.kind == "dividend_payment",
                RecordDate.record_date < today,
            )
            .distinct()
        ).scalars()
    )
    past_meetings = set(
        session.execute(
            select(ShareholderMeeting.ticker_id)
            .where(
                ShareholderMeeting.ticker_id.in_(ticker_ids),
                ShareholderMeeting.dividend_question.is_(True),
                ShareholderMeeting.meeting_date < today,
            )
            .distinct()
        ).scalars()
    )
    return past_record_dates | past_meetings


def add_item(
    session: Session, ticker_id: int, threshold_days: int, created_at: datetime
) -> WatchlistItem:
    """Создаёт сторожок (вызывается после проверки существования тикера)."""
    item = WatchlistItem(
        ticker_id=ticker_id,
        threshold_days=threshold_days,
        created_at=created_at,
    )
    session.add(item)
    session.flush()
    return item


def delete_item(session: Session, ticker: str) -> bool:
    """Удаляет сторожок по SECID; True, если запись удалена."""
    item = get_by_ticker(session, ticker)
    if item is None:
        return False

    session.delete(item)
    session.flush()
    return True
