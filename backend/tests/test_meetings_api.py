"""Тесты GET /api/v1/meetings и GET /api/v1/meetings/{id}."""

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models import Base, RecordDate, ShareholderMeeting, Ticker

FETCHED_AT = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
SOURCE_URL = "https://www.disclosure.ru/rus/corpnews/news.shtml?newsisn=1"


@pytest.fixture()
def session() -> Iterator[Session]:
    """Временная SQLite в памяти с собраниями, отсечками и тикерами."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as db_session:
        sber = Ticker(
            ticker="SBER",
            short_name="Сбербанк",
            full_name="Сбербанк России ПАО ао",
            isin="RU0009029540",
            logo_url="/static/logos/SBER.svg",
            last_price=Decimal("100.0000"),
            dsi=85,
            is_active=True,
            source_url="https://iss.moex.com/iss/example.json",
            fetched_at=FETCHED_AT,
        )
        gazp = Ticker(
            ticker="GAZP",
            short_name="Газпром",
            full_name="Газпром ПАО ао",
            isin="RU0007661625",
            last_price=None,
            is_active=True,
            source_url="https://iss.moex.com/iss/example.json",
            fetched_at=FETCHED_AT,
        )
        aflt = Ticker(
            ticker="AFLT",
            short_name="Аэрофлот",
            is_active=False,
            source_url="https://iss.moex.com/iss/example.json",
            fetched_at=FETCHED_AT,
        )
        db_session.add_all([sber, gazp, aflt])
        db_session.flush()

        sber_annual = ShareholderMeeting(
            ticker_id=sber.id,
            meeting_date=date(2026, 11, 20),
            meeting_type="annual",
            dividend_question=True,
            dividend_period="year",
            dividend_per_share=Decimal("10.0000"),
            description="О выплате дивидендов по итогам 2025 года",
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        sber_extra = ShareholderMeeting(
            ticker_id=sber.id,
            meeting_date=date(2026, 11, 27),
            meeting_type="extraordinary",
            dividend_question=True,
            dividend_period=None,
            dividend_per_share=None,
            description="Внеочередное собрание",
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        gazp_extra = ShareholderMeeting(
            ticker_id=gazp.id,
            meeting_date=date(2026, 11, 25),
            meeting_type="extraordinary",
            dividend_question=True,
            dividend_period="half_year",
            dividend_per_share=Decimal("5.0000"),
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        outside_range = ShareholderMeeting(
            ticker_id=sber.id,
            meeting_date=date(2027, 3, 15),
            meeting_type="annual",
            dividend_question=True,
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        no_dividend_question = ShareholderMeeting(
            ticker_id=sber.id,
            meeting_date=date(2026, 11, 10),
            meeting_type="extraordinary",
            dividend_question=False,
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        db_session.add_all(
            [sber_annual, sber_extra, gazp_extra, outside_range, no_dividend_question]
        )
        db_session.flush()

        db_session.add_all(
            [
                RecordDate(
                    ticker_id=sber.id,
                    meeting_id=sber_annual.id,
                    record_date=date(2026, 12, 1),
                    kind="dividend_payment",
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
                RecordDate(
                    ticker_id=sber.id,
                    meeting_id=sber_annual.id,
                    record_date=date(2026, 11, 10),
                    kind="meeting_participation",
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
                RecordDate(
                    ticker_id=gazp.id,
                    meeting_id=gazp_extra.id,
                    record_date=date(2026, 12, 5),
                    kind="dividend_payment",
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
            ]
        )
        db_session.commit()
        db_session.info["ids"] = {
            "sber_annual": sber_annual.id,
            "sber_extra": sber_extra.id,
            "gazp_extra": gazp_extra.id,
        }
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


def _range_params() -> dict[str, str]:
    return {"from": "2026-11-01", "to": "2026-11-30"}


def test_list_returns_dividend_meetings_sorted(client: TestClient) -> None:
    """В календарь попадают только собрания с вопросом о дивидендах, дата ASC."""
    response = client.get("/api/v1/meetings", params=_range_params())

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [item["meeting_date"] for item in body["items"]] == [
        "2026-11-20",
        "2026-11-25",
        "2026-11-27",
    ]
    assert [item["ticker"] for item in body["items"]] == ["SBER", "GAZP", "SBER"]


def test_meeting_dto_fields(client: TestClient) -> None:
    """DTO собрания содержит дивиденды, DSI, логотип и вложенную отсечку."""
    body = client.get("/api/v1/meetings", params=_range_params()).json()
    sber = body["items"][0]

    assert isinstance(sber["id"], int) and sber["id"] > 0
    assert sber["ticker"] == "SBER"
    assert sber["short_name"] == "Сбербанк"
    assert sber["logo_url"] == "/static/logos/SBER.svg"
    assert sber["meeting_type"] == "annual"
    assert sber["description"] == "О выплате дивидендов по итогам 2025 года"
    assert sber["dividend"] == {
        "period": "year",
        "amount_per_share": 10.0,
        "yield_percent": 10.0,
    }
    assert sber["dsi"] == 85
    assert sber["source_url"] == SOURCE_URL
    assert sber["fetched_at"] == "2026-10-21T12:00:00Z"
    assert sber["record_date"] == {
        "record_date": "2026-12-01",
        "kind": "dividend_payment",
        "fetched_at": "2026-10-21T12:00:00Z",
    }


def test_partial_dividend_terms_without_price(client: TestClient) -> None:
    """Известна сумма, но нет цены: доходность null, объект dividend остаётся."""
    body = client.get("/api/v1/meetings", params=_range_params()).json()
    gazp = body["items"][1]

    assert gazp["ticker"] == "GAZP"
    assert gazp["dividend"] == {
        "period": "half_year",
        "amount_per_share": 5.0,
        "yield_percent": None,
    }
    assert gazp["dsi"] is None
    assert gazp["record_date"]["record_date"] == "2026-12-05"


def test_meeting_without_terms_has_null_dividend(client: TestClient) -> None:
    """Если период и сумма не раскрыты, dividend и record_date равны null."""
    body = client.get("/api/v1/meetings", params=_range_params()).json()
    sber_extra = body["items"][2]

    assert sber_extra["ticker"] == "SBER"
    assert sber_extra["meeting_type"] == "extraordinary"
    assert sber_extra["dividend"] is None
    assert sber_extra["record_date"] is None


def test_non_dividend_meeting_excluded(client: TestClient) -> None:
    """Собрание с dividend_question = false не попадает в календарь."""
    response = client.get(
        "/api/v1/meetings", params={"from": "2026-11-10", "to": "2026-11-10"}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_ticker_filter_is_case_insensitive(client: TestClient) -> None:
    """Фильтр ticker нормализуется к верхнему регистру."""
    response = client.get("/api/v1/meetings", params={**_range_params(), "ticker": "sber"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["ticker"] for item in body["items"]} == {"SBER"}


def test_pagination(client: TestClient) -> None:
    """Пагинация применяется после фильтрации, total — размер выборки."""
    first = client.get(
        "/api/v1/meetings", params={**_range_params(), "page": 1, "page_size": 1}
    ).json()
    second = client.get(
        "/api/v1/meetings", params={**_range_params(), "page": 2, "page_size": 1}
    ).json()

    assert first["total"] == 3
    assert first["items"][0]["meeting_date"] == "2026-11-20"
    assert second["total"] == 3
    assert second["items"][0]["meeting_date"] == "2026-11-25"


def test_get_meeting_by_id(client: TestClient, session: Session) -> None:
    """Карточка собрания доступна по внутреннему id (deep-link модала)."""
    meeting_id = session.info["ids"]["sber_annual"]
    response = client.get(f"/api/v1/meetings/{meeting_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == meeting_id
    assert body["ticker"] == "SBER"
    assert body["dividend"]["amount_per_share"] == 10.0


def test_get_meeting_not_found(client: TestClient) -> None:
    """Несуществующий id — 404 с контрактным detail."""
    response = client.get("/api/v1/meetings/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "meeting not found"}


def test_from_greater_than_to(client: TestClient) -> None:
    """from > to — 422."""
    response = client.get(
        "/api/v1/meetings", params={"from": "2026-12-31", "to": "2026-11-01"}
    )

    assert response.status_code == 422
