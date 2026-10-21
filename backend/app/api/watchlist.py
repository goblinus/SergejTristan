"""Эндпоинты «сторожков» пользователя."""

from fastapi import APIRouter, HTTPException

from app.api.deps import PageDep, SessionDep
from app.schemas.common import Page
from app.schemas.watchlist import WatchlistCreate, WatchlistItem
from app.services import watchlist as watchlist_service

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=Page[WatchlistItem])
def list_watchlist(session: SessionDep, pagination: PageDep) -> Page[WatchlistItem]:
    """Сторожки с вычисленными next_record_date, days_to_cutoff и status."""
    items, total = watchlist_service.list_watchlist(
        session, page=pagination.page, page_size=pagination.page_size
    )
    return Page(items=items, page=pagination.page, page_size=pagination.page_size, total=total)


@router.post("", response_model=WatchlistItem, status_code=201)
def create_watchlist_item(payload: WatchlistCreate, session: SessionDep) -> WatchlistItem:
    """Добавить тикер в отслеживание (идемпотентно).

    TODO: проверка существования тикера (404), upsert сторожка (201/200).
    """
    raise HTTPException(status_code=501, detail="not implemented")


@router.delete("/{ticker}", status_code=204)
def delete_watchlist_item(ticker: str, session: SessionDep) -> None:
    """Снять тикер с отслеживания.

    TODO: удаление сторожка по SECID (регистр незначим); 404, если сторожка нет.
    """
    ticker_norm = ticker.strip().upper()
    raise HTTPException(status_code=501, detail=f"not implemented: {ticker_norm}")
