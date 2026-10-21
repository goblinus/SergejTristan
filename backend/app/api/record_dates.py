"""Эндпоинты календаря дат отсечки."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import PageDep, SessionDep
from app.schemas.common import Page
from app.schemas.record_date import RecordDate, RecordDateKind
from app.services import calendar as calendar_service

router = APIRouter(prefix="/record-dates", tags=["record-dates"])

DEFAULT_RANGE_DAYS = 90


@router.get("", response_model=Page[RecordDate])
def list_record_dates(
    session: SessionDep,
    pagination: PageDep,
    date_from: Annotated[date | None, Query(alias="from", description="Начало интервала")] = None,
    date_to: Annotated[date | None, Query(alias="to", description="Конец интервала")] = None,
    ticker: Annotated[str | None, Query(description="Фильтр по SECID")] = None,
    kind: Annotated[
        RecordDateKind, Query(description="Разновидность отсечки")
    ] = "dividend_payment",
) -> Page[RecordDate]:
    """Даты отсечки в интервале [from, to] включительно, сортировка record_date ASC."""
    start = date_from or date.today()
    end = date_to or start + timedelta(days=DEFAULT_RANGE_DAYS)
    if start > end:
        raise HTTPException(status_code=422, detail="from must be <= to")

    ticker_norm = ticker.strip().upper() if ticker else None
    return calendar_service.list_record_dates(
        session,
        date_from=start,
        date_to=end,
        ticker=ticker_norm,
        kind=kind,
        page=pagination.page,
        page_size=pagination.page_size,
    )
