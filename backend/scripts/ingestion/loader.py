"""Идемпотентная загрузка нормализованных DTO в БД через репозитории."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories import tickers as tickers_repo
from app.repositories.tickers import TickerUpsert
from scripts.ingestion.normalize import (
    NormalizedDividendMetrics,
    NormalizedMeeting,
    NormalizedRecordDate,
    NormalizedTicker,
)


@dataclass
class LoadStats:
    """Итог загрузки одной сущности."""

    inserted: int = 0
    updated: int = 0
    skipped: int = 0


def load_tickers(session: Session, items: list[NormalizedTicker]) -> LoadStats:
    """Upsert тикеров по бизнес-ключу `ticker`."""
    upserts = [
        TickerUpsert(
            ticker=item.ticker,
            short_name=item.short_name,
            full_name=item.full_name,
            isin=item.isin,
            board=item.board,
            lot_size=item.lot_size,
            last_price=item.last_price,
            price_updated_at=item.fetched_at if item.last_price is not None else None,
            source_url=item.source_url,
            fetched_at=item.fetched_at,
        )
        for item in items
    ]
    inserted, updated = tickers_repo.upsert_tickers(session, upserts)
    return LoadStats(inserted=inserted, updated=updated)


def deactivate_missing_tickers(
    session: Session,
    active_tickers: set[str],
    *,
    board: str,
    source_url: str,
) -> int:
    """Деактивирует тикеры доски, не попавшие в текущий успешный сбор."""
    return tickers_repo.deactivate_missing(
        session, active_tickers, board=board, source_url=source_url
    )


def load_meetings(session: Session, items: list[NormalizedMeeting]) -> LoadStats:
    """Upsert собраний по (ticker_id, meeting_date, meeting_type).

    TODO: реализовать после появления upsert-функций в app/repositories/meetings.py.
    """
    raise NotImplementedError


def load_record_dates(session: Session, items: list[NormalizedRecordDate]) -> LoadStats:
    """Upsert дат отсечки по (ticker_id, record_date, kind).

    TODO: реализовать после появления upsert-функций в app/repositories/record_dates.py.
    """
    raise NotImplementedError


def load_dividend_metrics(
    session: Session, items: list[NormalizedDividendMetrics]
) -> LoadStats:
    """Обновление снапшота DSI у тикеров (`dsi`, `dsi_updated_at`).

    TODO: реализовать после появления update-функции в app/repositories/tickers.py.
    """
    raise NotImplementedError
