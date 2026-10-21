"""Сервис «сторожков»: расчёт статуса и дней до отсечки, сборка DTO."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.repositories import watchlist as watchlist_repo
from app.schemas.watchlist import WatchlistItem

if TYPE_CHECKING:
    from app.models.record_date import RecordDate
    from app.models.ticker import Ticker
    from app.models.watchlist_item import WatchlistItem as WatchlistItemModel


def calc_days_to_cutoff(today: date, next_record_date: date | None) -> int | None:
    """Число суток от today до ближайшей отсечки; None, если даты нет."""
    if next_record_date is None:
        return None
    return (next_record_date - today).days


def calc_status(
    today: date,
    threshold_days: int,
    soon_days: int,
    next_record_date: date | None,
    has_past_dates: bool,
) -> str:
    """Статус сторожка по канонической шкале.

    Порядок проверок: critical -> hot -> near -> far; без будущей даты —
    past (есть прошедшие) или no_date (записей нет).
    """
    if next_record_date is None:
        return "past" if has_past_dates else "no_date"

    days = (next_record_date - today).days
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
    ticker: "Ticker",
    next_record_date: "RecordDate | None",
    today: date,
    soon_days: int,
    has_past_dates: bool,
) -> WatchlistItem:
    """Собирает DTO сторожка с вычисленными полями.

    TODO: next_meeting_date (через record_dates.meeting_id) и next_dividend
    (условия ближайшего собрания) — после реализации выборок репозитория.
    """
    cutoff = next_record_date.record_date if next_record_date is not None else None
    return WatchlistItem(
        ticker=ticker.ticker,
        short_name=ticker.short_name,
        logo_url=ticker.logo_url,
        threshold_days=item.threshold_days,
        created_at=item.created_at,
        next_record_date=cutoff,
        next_meeting_date=None,
        days_to_cutoff=calc_days_to_cutoff(today, cutoff),
        status=calc_status(today, item.threshold_days, soon_days, cutoff, has_past_dates),
        next_dividend=None,
        dsi=ticker.dsi,
    )


def list_watchlist(session: Session, page: int, page_size: int) -> tuple[list[WatchlistItem], int]:
    """Список сторожков с вычисленными полями.

    TODO: выборка ближайших отсечек и прошедших дат по тикерам одним запросом,
    сортировка по (status_rank, next_record_date, ticker).
    """
    rows, total = watchlist_repo.list_items(session, page=page, page_size=page_size)
    return rows, total
