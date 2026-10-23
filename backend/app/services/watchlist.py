"""Сервис «сторожков»: расчёт статуса и дней до даты события, CRUD, сборка DTO."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories import tickers as tickers_repo
from app.repositories import watchlist as watchlist_repo
from app.schemas.watchlist import WatchlistCreate, WatchlistItem
from app.services.dividends import build_dividend_terms, get_dsi

if TYPE_CHECKING:
    from app.models.record_date import RecordDate
    from app.models.shareholder_meeting import ShareholderMeeting
    from app.models.watchlist_item import WatchlistItem as WatchlistItemModel


@dataclass(frozen=True, slots=True)
class WatchEvent:
    """Ближайшее будущее дивидендное событие сторожка.

    Либо отсечка `dividend_payment` (тогда `meeting` — связанное собрание или
    None), либо само собрание с дивидендным вопросом (fallback).
    """

    event_date: date
    meeting: "ShareholderMeeting | None"


def select_event(
    next_record_date: "RecordDate | None",
    next_meeting: "ShareholderMeeting | None",
) -> WatchEvent | None:
    """Выбирает событие сторожка: отсечка приоритетнее собрания.

    Отсечка `dividend_payment` выигрывает, даже если ближайшее собрание
    наступает раньше. Собрание используется, только когда будущей отсечки нет.
    """
    if next_record_date is not None:
        return WatchEvent(next_record_date.record_date, next_record_date.meeting)
    if next_meeting is not None:
        return WatchEvent(next_meeting.meeting_date, next_meeting)
    return None


def calc_days_to_event(today: date, event_date: date | None) -> int | None:
    """Число суток от today до даты события; None, если даты нет."""
    if event_date is None:
        return None
    return (event_date - today).days


def calc_status(
    today: date,
    threshold_days: int,
    soon_days: int,
    event_date: date | None,
    has_past_events: bool,
) -> str:
    """Статус сторожка по канонической шкале.

    Порядок проверок: critical -> hot -> near -> far; без будущего события —
    past (есть прошедшие события) или no_date (событий нет).
    """
    if event_date is None:
        return "past" if has_past_events else "no_date"

    days = (event_date - today).days
    if days < 0:
        return "past"
    if days == 0:
        return "critical"
    if days <= threshold_days:
        return "hot"
    if days <= soon_days:
        return "near"
    return "far"


def build_watchlist_item(
    item: "WatchlistItemModel",
    event: WatchEvent | None,
    today: date,
    soon_days: int,
    has_past_events: bool,
) -> WatchlistItem:
    """Собирает DTO сторожка с вычисленными полями."""
    ticker = item.ticker
    event_date = event.event_date if event is not None else None
    meeting = event.meeting if event is not None else None

    return WatchlistItem(
        ticker=ticker.ticker,
        short_name=ticker.short_name,
        logo_url=ticker.logo_url,
        threshold_days=item.threshold_days,
        created_at=item.created_at,
        next_record_date=event_date,
        next_meeting_date=meeting.meeting_date if meeting is not None else None,
        days_to_event=calc_days_to_event(today, event_date),
        status=calc_status(today, item.threshold_days, soon_days, event_date, has_past_events),
        next_dividend=build_dividend_terms(meeting, ticker) if meeting is not None else None,
        dsi=get_dsi(ticker),
    )


def _status_rank(status: str) -> int:
    """Ранг группы сортировки: датированные -> no_date -> past."""
    if status == "no_date":
        return 1
    if status == "past":
        return 2
    return 0


def _sort_key(item: WatchlistItem) -> tuple[int, date, str]:
    """Канонический порядок списка S2: (status_rank, next_record_date, ticker)."""
    return (_status_rank(item.status), item.next_record_date or date.max, item.ticker)


def _build_items(
    session: Session, items: "list[WatchlistItemModel]", today: date
) -> list[WatchlistItem]:
    """Собирает DTO для набора сторожков, вычисляя ближайшие события пачкой.

    Отсечки и собрания выбираются двумя запросами по набору ticker_id, поэтому
    N+1 не возникает. Прошедшие события нужны только для различения no_date/past.
    """
    ticker_ids = {item.ticker_id for item in items}
    next_dates = watchlist_repo.get_next_record_dates(session, ticker_ids, today)
    next_meetings = watchlist_repo.get_next_meetings(session, ticker_ids, today)
    past_ids = watchlist_repo.get_ticker_ids_with_past_events(session, ticker_ids, today)
    soon_days = get_settings().watch_soon_days

    return [
        build_watchlist_item(
            item,
            select_event(next_dates.get(item.ticker_id), next_meetings.get(item.ticker_id)),
            today,
            soon_days,
            item.ticker_id in past_ids,
        )
        for item in items
    ]


def list_watchlist(session: Session, page: int, page_size: int) -> tuple[list[WatchlistItem], int]:
    """Список сторожков с вычисленными полями и канонической сортировкой."""
    today = date.today()
    dtos = _build_items(session, watchlist_repo.list_items(session), today)
    dtos.sort(key=_sort_key)

    total = len(dtos)
    start = (page - 1) * page_size
    return dtos[start : start + page_size], total


def create_watchlist_item(
    session: Session, payload: WatchlistCreate
) -> tuple[WatchlistItem, bool] | None:
    """Добавляет сторожок идемпотентно.

    Возвращает (DTO, создан_ли) или None, если тикер отсутствует в справочнике.
    При существующем сторожке обновляет `threshold_days`, если он передан.
    """
    ticker = tickers_repo.get_by_ticker(session, payload.ticker)
    if ticker is None:
        return None

    existing = watchlist_repo.get_by_ticker(session, payload.ticker)
    if existing is not None:
        if payload.threshold_days is not None:
            existing.threshold_days = payload.threshold_days
        session.commit()
        created = False
    else:
        threshold_days = (
            payload.threshold_days
            if payload.threshold_days is not None
            else get_settings().watch_default_threshold_days
        )
        watchlist_repo.add_item(
            session, ticker.id, threshold_days, datetime.now(UTC)
        )
        session.commit()
        created = True

    item = watchlist_repo.get_by_ticker(session, payload.ticker)
    if item is None:  # pragma: no cover — защита от гонки уникального ключа
        return None

    today = date.today()
    dto = _build_items(session, [item], today)[0]
    return dto, created


def delete_watchlist_item(session: Session, ticker: str) -> bool:
    """Удаляет сторожок по SECID; False, если записи нет."""
    deleted = watchlist_repo.delete_item(session, ticker)
    if deleted:
        session.commit()
    return deleted
