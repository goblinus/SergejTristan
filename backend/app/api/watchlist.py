"""Эндпоинты «сторожков» пользователя."""

from fastapi import APIRouter, HTTPException, Response

from app.api.deps import PageDep, SessionDep
from app.schemas.common import Page
from app.schemas.watchlist import WatchlistCreate, WatchlistItem
from app.services import watchlist as watchlist_service

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=Page[WatchlistItem])
def list_watchlist(session: SessionDep, pagination: PageDep) -> Page[WatchlistItem]:
    """Сторожки с вычисленными next_record_date, days_to_event и status."""
    items, total = watchlist_service.list_watchlist(
        session, page=pagination.page, page_size=pagination.page_size
    )
    return Page(items=items, page=pagination.page, page_size=pagination.page_size, total=total)


@router.post(
    "",
    response_model=WatchlistItem,
    status_code=201,
    responses={200: {"model": WatchlistItem, "description": "Сторожок уже существовал"}},
)
def create_watchlist_item(
    payload: WatchlistCreate, session: SessionDep, response: Response
) -> WatchlistItem:
    """Добавить тикер в отслеживание (идемпотентно).

    201 — создан новый сторожок; 200 — тикер уже отслеживается (при переданном
    `threshold_days` значение обновляется); 404 — тикер не найден.
    """
    result = watchlist_service.create_watchlist_item(session, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="ticker not found")

    item, created = result
    if not created:
        response.status_code = 200
    return item


@router.delete("/{ticker}", status_code=204)
def delete_watchlist_item(ticker: str, session: SessionDep) -> None:
    """Снять тикер с отслеживания по SECID (регистр незначим)."""
    ticker_norm = ticker.strip().upper()
    if not ticker_norm:
        raise HTTPException(status_code=404, detail="watchlist item not found")

    if not watchlist_service.delete_watchlist_item(session, ticker_norm):
        raise HTTPException(status_code=404, detail="watchlist item not found")
