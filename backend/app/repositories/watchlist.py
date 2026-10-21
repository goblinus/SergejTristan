"""Репозиторий «сторожков»."""

from sqlalchemy.orm import Session

from app.models.watchlist_item import WatchlistItem


def list_items(
    session: Session, page: int = 1, page_size: int = 50
) -> tuple[list[WatchlistItem], int]:
    """Сторожки с тикером (join), канонический порядок списка S2.

    TODO: реализовать join с tickers, предварительный расчёт статуса и сортировку
    по (status_rank, next_record_date, ticker), offset/limit и count.
    Пока — пустой результат для каркаса API.
    """
    return [], 0


def get_by_ticker(session: Session, ticker: str) -> WatchlistItem | None:
    """Сторожок по SECID тикера.

    TODO: реализовать выборку по бизнес-ключу (join с tickers).
    """
    return None


def add_item(session: Session, ticker_id: int, threshold_days: int) -> WatchlistItem:
    """Создаёт сторожок.

    TODO: реализовать вставку записи (вызывается после проверки существования тикера).
    """
    raise NotImplementedError


def delete_item(session: Session, ticker: str) -> bool:
    """Удаляет сторожок по SECID; True, если запись удалена.

    TODO: реализовать удаление по бизнес-ключу.
    """
    raise NotImplementedError
