"""Эндпоинты календаря собраний акционеров."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import PageDep, SessionDep
from app.schemas.common import Page
from app.schemas.meeting import Meeting
from app.services import calendar as calendar_service

router = APIRouter(prefix="/meetings", tags=["meetings"])

DEFAULT_RANGE_DAYS = 90


@router.get("", response_model=Page[Meeting])
def list_meetings(
    session: SessionDep,
    pagination: PageDep,
    date_from: Annotated[date | None, Query(alias="from", description="Начало интервала")] = None,
    date_to: Annotated[date | None, Query(alias="to", description="Конец интервала")] = None,
    ticker: Annotated[str | None, Query(description="Фильтр по SECID")] = None,
) -> Page[Meeting]:
    """Собрания с вопросом о дивидендах в интервале [from, to] включительно."""
    start = date_from or date.today()
    end = date_to or start + timedelta(days=DEFAULT_RANGE_DAYS)
    if start > end:
        raise HTTPException(status_code=422, detail="from must be <= to")

    ticker_norm = ticker.strip().upper() if ticker else None
    return calendar_service.list_meetings(
        session,
        date_from=start,
        date_to=end,
        ticker=ticker_norm,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{meeting_id}", response_model=Meeting)
def get_meeting(meeting_id: int, session: SessionDep) -> Meeting:
    """Карточка собрания по внутреннему id (deep-link модала деталей)."""
    meeting = calendar_service.get_meeting(session, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting not found")
    return meeting
