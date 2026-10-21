"""Тесты GET /api/v1/tickers на временной БД."""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models import Base, Ticker

FETCHED_AT = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
SOURCE_URL = "https://iss.moex.com/iss/example.json"


@pytest.fixture()
def session() -> Session:
    """Временная SQLite в памяти с тикерами для проверки API."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as db_session:
        db_session.add_all(
            [
                Ticker(
                    ticker="SBER",
                    short_name="Сбербанк",
                    full_name="Сбербанк России ПАО ао",
                    isin="RU0009029540",
                    board="TQBR",
                    lot_size=10,
                    logo_url="/static/logos/SBER.svg",
                    is_active=True,
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
                Ticker(
                    ticker="GAZP",
                    short_name="Газпром",
                    full_name="Газпром ПАО ао",
                    isin="RU0007661625",
                    board="TQBR",
                    lot_size=10,
                    is_active=True,
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
                Ticker(
                    ticker="AFLT",
                    short_name="Аэрофлот",
                    board="TQBR",
                    is_active=False,
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
            ]
        )
        db_session.commit()
        yield db_session

    engine.dispose()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    """TestClient с подменой зависимости сессии на временную БД."""

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_returns_active_tickers_sorted(client: TestClient) -> None:
    """Только активные тикеры, сортировка ticker ASC, конверт Page."""
    response = client.get("/api/v1/tickers")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["total"] == 2
    assert [item["ticker"] for item in body["items"]] == ["GAZP", "SBER"]


def test_ticker_dto_fields(client: TestClient) -> None:
    """DTO содержит поля контракта и не отдаёт source_url."""
    sber = client.get("/api/v1/tickers", params={"q": "sber"}).json()["items"][0]

    assert sber["ticker"] == "SBER"
    assert sber["short_name"] == "Сбербанк"
    assert sber["full_name"] == "Сбербанк России ПАО ао"
    assert sber["isin"] == "RU0009029540"
    assert sber["board"] == "TQBR"
    assert sber["lot_size"] == 10
    assert sber["logo_url"] == "/static/logos/SBER.svg"
    assert sber["is_active"] is True
    assert sber["fetched_at"] == "2026-10-21T12:00:00Z"
    assert "source_url" not in sber


def test_search_is_case_insensitive_for_cyrillic(client: TestClient) -> None:
    """Поиск q по short_name не зависит от регистра кириллицы."""
    response = client.get("/api/v1/tickers", params={"q": "сбер"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["ticker"] == "SBER"


def test_search_matches_ticker_and_short_name(client: TestClient) -> None:
    """Подстрока ищется и по SECID, и по краткому наименованию."""
    by_ticker = client.get("/api/v1/tickers", params={"q": "gaz"}).json()
    by_name = client.get("/api/v1/tickers", params={"q": "ГАЗ"}).json()

    assert by_ticker["items"][0]["ticker"] == "GAZP"
    assert by_name["items"][0]["ticker"] == "GAZP"


def test_inactive_ticker_excluded_from_search(client: TestClient) -> None:
    """Неактивный тикер не возвращается даже при совпадении поиска."""
    response = client.get("/api/v1/tickers", params={"q": "аэрофлот"})

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_pagination(client: TestClient) -> None:
    """Пагинация применяется после фильтрации; total — размер выборки."""
    first = client.get("/api/v1/tickers", params={"page": 1, "page_size": 1}).json()
    second = client.get("/api/v1/tickers", params={"page": 2, "page_size": 1}).json()

    assert first["total"] == 2
    assert first["items"][0]["ticker"] == "GAZP"
    assert second["total"] == 2
    assert second["items"][0]["ticker"] == "SBER"


def test_blank_query_returns_all(client: TestClient) -> None:
    """Пустая строка q не фильтрует список."""
    response = client.get("/api/v1/tickers", params={"q": "   "})

    assert response.status_code == 200
    assert response.json()["total"] == 2
