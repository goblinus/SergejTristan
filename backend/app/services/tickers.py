"""Сервис тикеров: список с поиском и пагинацией."""

from sqlalchemy.orm import Session

from app.repositories import tickers as tickers_repo
from app.schemas.common import Page
from app.schemas.ticker import Ticker


def to_dto(ticker) -> Ticker:
    """Преобразует ORM-модель тикера в DTO (source_url наружу не отдаётся)."""
    return Ticker(
        ticker=ticker.ticker,
        short_name=ticker.short_name,
        full_name=ticker.full_name,
        isin=ticker.isin,
        board=ticker.board,
        lot_size=ticker.lot_size,
        logo_url=ticker.logo_url,
        is_active=ticker.is_active,
        fetched_at=ticker.fetched_at,
    )


def list_tickers(
    session: Session, q: str | None, page: int, page_size: int
) -> Page[Ticker]:
    """Список активных тикеров: фильтр q по ticker/short_name, сортировка ticker ASC."""
    rows, total = tickers_repo.list_tickers(session, q=q, page=page, page_size=page_size)
    return Page(items=[to_dto(row) for row in rows], page=page, page_size=page_size, total=total)
