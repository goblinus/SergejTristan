"""Репозиторий тикеров."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticker import Ticker


@dataclass(frozen=True, slots=True)
class TickerUpsert:
    """Данные тикера для идемпотентного upsert из скриптов сбора."""

    ticker: str
    short_name: str
    full_name: str | None
    isin: str | None
    board: str | None
    lot_size: int | None
    last_price: Decimal | None
    price_updated_at: datetime | None
    source_url: str
    fetched_at: datetime


def list_tickers(
    session: Session,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Ticker], int]:
    """Активные тикеры: поиск q по ticker/short_name, сортировка ticker ASC.

    Поиск выполняется в Python: SQLite LIKE/lower() не сворачивают регистр
    кириллицы (пример контракта — `q=сбер`). Активный список MOEX — около
    500 записей, для MVP загрузка его целиком допустима.
    """
    rows = list(
        session.execute(
            select(Ticker).where(Ticker.is_active.is_(True)).order_by(Ticker.ticker)
        ).scalars()
    )

    if q is not None and q.strip():
        needle = q.strip().casefold()
        rows = [
            row
            for row in rows
            if needle in row.ticker.casefold() or needle in row.short_name.casefold()
        ]

    total = len(rows)
    start = (page - 1) * page_size
    return rows[start : start + page_size], total


def get_by_ticker(session: Session, ticker: str) -> Ticker | None:
    """Тикер по SECID (верхний регистр).

    TODO: реализовать выборку по бизнес-ключу.
    """
    return None


def upsert_tickers(session: Session, items: Iterable[TickerUpsert]) -> tuple[int, int]:
    """Идемпотентный upsert по бизнес-ключу `ticker`.

    Возвращает (вставлено, обновлено). Существующие записи получают новые
    поля данных, `source_url`, `fetched_at` и `is_active = true`.
    """
    by_ticker = {item.ticker: item for item in items}
    if not by_ticker:
        return 0, 0

    existing = {
        row.ticker: row
        for row in session.execute(
            select(Ticker).where(Ticker.ticker.in_(by_ticker))
        ).scalars()
    }

    inserted = 0
    updated = 0

    for ticker, item in by_ticker.items():
        row = existing.get(ticker)
        if row is None:
            row = Ticker(
                ticker=item.ticker,
                short_name=item.short_name,
                full_name=item.full_name,
                isin=item.isin,
                board=item.board,
                lot_size=item.lot_size,
                last_price=item.last_price,
                price_updated_at=item.price_updated_at if item.last_price is not None else None,
                is_active=True,
                source_url=item.source_url,
                fetched_at=item.fetched_at,
            )
            session.add(row)
            inserted += 1
        else:
            row.short_name = item.short_name
            row.full_name = item.full_name
            row.isin = item.isin
            row.board = item.board
            row.lot_size = item.lot_size
            if item.last_price is not None:
                row.last_price = item.last_price
                row.price_updated_at = item.price_updated_at or item.fetched_at
            row.is_active = True
            row.source_url = item.source_url
            row.fetched_at = item.fetched_at
            updated += 1

    session.flush()
    return inserted, updated


def deactivate_missing(
    session: Session,
    keep_tickers: set[str],
    *,
    board: str,
    source_url: str,
) -> int:
    """Помечает `is_active = false` тикеры этой доски, отсутствующие в выборке.

    Удаление не выполняется: у тикера могут быть собрания и сторожки.
    Пустой `keep_tickers` не деактивирует ничего — защита от массовой пометки
    при пустом ответе источника.
    """
    if not keep_tickers:
        return 0

    rows = session.execute(
        select(Ticker).where(
            Ticker.board == board,
            Ticker.is_active.is_(True),
            Ticker.source_url.like(f"{source_url}%"),
            Ticker.ticker.notin_(keep_tickers),
        )
    ).scalars()

    deactivated = 0
    for row in rows:
        row.is_active = False
        deactivated += 1

    session.flush()
    return deactivated
