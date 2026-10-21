"""Smoke-тесты API: /health, пустые списки, коды ошибок каркаса."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models import Base


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """TestClient с прогоном lifespan и пустой in-memory БД."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def test_health(client: TestClient) -> None:
    """/health отвечает 200 и статусом ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tickers_empty_page(client: TestClient) -> None:
    """Пустой справочник тикеров отдаётся пустым конвертом Page."""
    response = client.get("/api/v1/tickers")
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_tickers_search_param(client: TestClient) -> None:
    """Поиск q принимается и возвращает пустой Page (репозиторий — заглушка)."""
    response = client.get("/api/v1/tickers", params={"q": "сбер"})
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_meetings_empty_page(client: TestClient) -> None:
    """Календарь собраний по умолчанию пуст."""
    response = client.get("/api/v1/meetings")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_meetings_invalid_range(client: TestClient) -> None:
    """from > to — ошибка валидации 422."""
    response = client.get(
        "/api/v1/meetings", params={"from": "2026-12-31", "to": "2026-10-19"}
    )
    assert response.status_code == 422


def test_meeting_not_found(client: TestClient) -> None:
    """Карточка несуществующего собрания — 404."""
    response = client.get("/api/v1/meetings/42")
    assert response.status_code == 404
    assert response.json() == {"detail": "meeting not found"}


def test_record_dates_empty_page(client: TestClient) -> None:
    """Календарь отсечек по умолчанию пуст."""
    response = client.get("/api/v1/record-dates")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_record_dates_invalid_kind(client: TestClient) -> None:
    """Неизвестный kind — 422."""
    response = client.get("/api/v1/record-dates", params={"kind": "unknown"})
    assert response.status_code == 422


def test_watchlist_empty_page(client: TestClient) -> None:
    """Список сторожков пуст."""
    response = client.get("/api/v1/watchlist")
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_watchlist_create_not_implemented(client: TestClient) -> None:
    """POST /watchlist пока возвращает 501."""
    response = client.post("/api/v1/watchlist", json={"ticker": "sber", "threshold_days": 14})
    assert response.status_code == 501
    assert response.json() == {"detail": "not implemented"}


def test_watchlist_create_threshold_validation(client: TestClient) -> None:
    """threshold_days вне 1..365 — 422."""
    response = client.post("/api/v1/watchlist", json={"ticker": "SBER", "threshold_days": 0})
    assert response.status_code == 422


def test_watchlist_create_ticker_required(client: TestClient) -> None:
    """Пустое тело без ticker — 422."""
    response = client.post("/api/v1/watchlist", json={})
    assert response.status_code == 422


def test_watchlist_delete_not_implemented(client: TestClient) -> None:
    """DELETE /watchlist/{ticker} пока возвращает 501."""
    response = client.delete("/api/v1/watchlist/sber")
    assert response.status_code == 501
    assert response.json()["detail"].startswith("not implemented")


@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page_size": 0}, {"page_size": 101}],
)
def test_pagination_validation(client: TestClient, params: dict) -> None:
    """Некорректные page/page_size — 422."""
    response = client.get("/api/v1/tickers", params=params)
    assert response.status_code == 422
