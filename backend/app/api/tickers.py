"""Эндпоинты тикеров."""

from fastapi import APIRouter, Query

from app.api.deps import PageDep, SessionDep
from app.schemas.common import Page
from app.schemas.ticker import Ticker
from app.services import tickers as tickers_service

router = APIRouter(prefix="/tickers", tags=["tickers"])


@router.get("", response_model=Page[Ticker])
def list_tickers(
    session: SessionDep,
    pagination: PageDep,
    q: str | None = Query(None, description="Подстрока для поиска по ticker и short_name"),
) -> Page[Ticker]:
    """Список активных тикеров с поиском и пагинацией, сортировка ticker ASC."""
    return tickers_service.list_tickers(
        session, q=q, page=pagination.page, page_size=pagination.page_size
    )
