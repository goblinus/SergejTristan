"""Тесты загрузчика тикеров: идемпотентный upsert и деактивация."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Ticker
from scripts.ingestion.loader import deactivate_missing_tickers, load_tickers
from scripts.ingestion.normalize import NormalizedTicker
from scripts.ingestion.sources.moex_iss import BASE_URL

FETCHED_AT = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


def _item(
    ticker: str,
    short_name: str = "Компания",
    *,
    board: str = "TQBR",
    last_price: Decimal | None = Decimal("100.0"),
) -> NormalizedTicker:
    return NormalizedTicker(
        ticker=ticker,
        short_name=short_name,
        full_name=f"{short_name} ПАО ао",
        isin="RU0000000000",
        board=board,
        lot_size=10,
        last_price=last_price,
        source_url=BASE_URL,
        fetched_at=FETCHED_AT,
    )


@pytest.fixture()
def session() -> Session:
    """Временная SQLite в памяти со схемой из ORM-моделей."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db_session:
        yield db_session
    engine.dispose()


def test_load_inserts_tickers(session: Session) -> None:
    """Первая загрузка вставляет тикеры и заполняет поля цены."""
    stats = load_tickers(session, [_item("SBER"), _item("GAZP")])
    session.commit()

    rows = {row.ticker: row for row in session.execute(select(Ticker)).scalars()}
    assert stats.inserted == 2
    assert stats.updated == 0
    assert set(rows) == {"SBER", "GAZP"}
    assert rows["SBER"].last_price == Decimal("100.0")
    # SQLite не хранит tzinfo: значение читается наивным, но соответствует UTC.
    assert rows["SBER"].price_updated_at.replace(tzinfo=UTC) == FETCHED_AT
    assert rows["SBER"].is_active is True


def test_load_is_idempotent(session: Session) -> None:
    """Повторная загрузка обновляет запись, а не создаёт дубль."""
    load_tickers(session, [_item("SBER", "Сбербанк")])
    stats = load_tickers(session, [_item("SBER", "Сбербанк России")])
    session.commit()

    rows = list(session.execute(select(Ticker)).scalars())
    assert stats.inserted == 0
    assert stats.updated == 1
    assert len(rows) == 1
    assert rows[0].short_name == "Сбербанк России"


def test_load_keeps_last_known_price(session: Session) -> None:
    """Отсутствие цены в новом ответе не стирает последнюю известную цену."""
    load_tickers(session, [_item("SBER", last_price=Decimal("100.0"))])
    load_tickers(session, [_item("SBER", last_price=None)])
    session.commit()

    row = session.execute(select(Ticker)).scalar_one()
    assert row.last_price == Decimal("100.0")
    assert row.price_updated_at.replace(tzinfo=UTC) == FETCHED_AT


def test_deactivate_missing(session: Session) -> None:
    """Отсутствующий в выборке тикер доски помечается неактивным, не удаляется."""
    load_tickers(session, [_item("SBER"), _item("GAZP"), _item("MTLR")])
    deactivated = deactivate_missing_tickers(
        session, {"SBER", "GAZP"}, board="TQBR", source_url=BASE_URL
    )
    session.commit()

    rows = {row.ticker: row for row in session.execute(select(Ticker)).scalars()}
    assert deactivated == 1
    assert len(rows) == 3
    assert rows["MTLR"].is_active is False
    assert rows["SBER"].is_active is True


def test_deactivate_is_idempotent(session: Session) -> None:
    """Повторная деактивация не находит активных отсутствующих тикеров."""
    load_tickers(session, [_item("SBER"), _item("MTLR")])
    deactivate_missing_tickers(session, {"SBER"}, board="TQBR", source_url=BASE_URL)
    deactivated = deactivate_missing_tickers(
        session, {"SBER"}, board="TQBR", source_url=BASE_URL
    )
    session.commit()

    assert deactivated == 0


def test_deactivate_skips_empty_selection(session: Session) -> None:
    """Пустая выборка не деактивирует тикеры (защита от пустого ответа)."""
    load_tickers(session, [_item("SBER")])
    deactivated = deactivate_missing_tickers(
        session, set(), board="TQBR", source_url=BASE_URL
    )
    session.commit()

    row = session.execute(select(Ticker)).scalar_one()
    assert deactivated == 0
    assert row.is_active is True


def test_deactivate_ignores_other_board(session: Session) -> None:
    """Тикеры другой доски не затрагиваются деактивацией TQBR."""
    load_tickers(session, [_item("SBER"), _item("AFLT", board="SMAL")])
    deactivate_missing_tickers(session, {"SBER"}, board="TQBR", source_url=BASE_URL)
    session.commit()

    rows = {row.ticker: row for row in session.execute(select(Ticker)).scalars()}
    assert rows["AFLT"].is_active is True


def test_load_reactivates_ticker(session: Session) -> None:
    """Появление тикера в новом сборе возвращает is_active = true."""
    load_tickers(session, [_item("MTLR")])
    deactivate_missing_tickers(session, {"SBER"}, board="TQBR", source_url=BASE_URL)
    load_tickers(session, [_item("MTLR")])
    session.commit()

    row = session.execute(select(Ticker)).scalar_one()
    assert row.is_active is True
