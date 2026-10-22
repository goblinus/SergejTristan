"""Тесты GET/POST/DELETE /api/v1/watchlist и расчёта статуса сторожка."""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models import Base, RecordDate, ShareholderMeeting, Ticker, WatchlistItem
from app.services.watchlist import calc_days_to_event, calc_status

FETCHED_AT = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
SOURCE_URL = "https://www.disclosure.ru/rus/corpnews/news.shtml?newsisn=1"
TODAY = date.today()


def _iso(value: date) -> str:
    return value.isoformat()


def _make_ticker(ticker: str, **kwargs) -> Ticker:
    defaults = {
        "short_name": f"{ticker} name",
        "is_active": True,
        "source_url": "https://iss.moex.com/iss/example.json",
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return Ticker(ticker=ticker, **defaults)


@pytest.fixture()
def session() -> Iterator[Session]:
    """Временная SQLite в памяти: сторожки во всех состояниях шкалы.

    Покрыты оба источника события: будущая отсечка `dividend_payment` и
    fallback на ближайшее собрание с дивидендным вопросом.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as db_session:
        sber = _make_ticker(
            "SBER",
            short_name="Сбербанк",
            logo_url="/static/logos/SBER.svg",
            last_price=Decimal("100.0000"),
            dsi=85,
        )
        mgnt = _make_ticker("MGNT", short_name="Магнит")
        gazp = _make_ticker("GAZP", short_name="Газпром")
        aflt = _make_ticker("AFLT", short_name="Аэрофлот", is_active=False)
        lkoh = _make_ticker(
            "LKOH",
            short_name="Лукойл",
            last_price=Decimal("50.0000"),
        )
        tatn = _make_ticker(
            "TATN",
            short_name="Татнефть",
            last_price=Decimal("150.0000"),
        )
        mtss = _make_ticker("MTSS", short_name="МТС")
        sngs = _make_ticker("SNGS", short_name="Сургутнефтегаз")
        rosn = _make_ticker("ROSN", short_name="Роснефть")
        nvtk = _make_ticker("NVTK", short_name="Новатэк")
        plzl = _make_ticker("PLZL", short_name="Полюс")
        irao = _make_ticker(
            "IRAO",
            short_name="Интер РАО",
            last_price=Decimal("10.0000"),
        )
        db_session.add_all(
            [sber, mgnt, gazp, aflt, lkoh, tatn, mtss, sngs, rosn, nvtk, plzl, irao]
        )
        db_session.flush()

        sber_meeting = ShareholderMeeting(
            ticker_id=sber.id,
            meeting_date=TODAY + timedelta(days=2),
            meeting_type="annual",
            dividend_question=True,
            dividend_period="year",
            dividend_per_share=Decimal("10.0000"),
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        sber_far_meeting = ShareholderMeeting(
            ticker_id=sber.id,
            meeting_date=TODAY + timedelta(days=29),
            meeting_type="extraordinary",
            dividend_question=True,
            dividend_period="quarter",
            dividend_per_share=Decimal("20.0000"),
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        lkoh_meeting = ShareholderMeeting(
            ticker_id=lkoh.id,
            meeting_date=TODAY + timedelta(days=1),
            meeting_type="annual",
            dividend_question=True,
            dividend_period="quarter",
            dividend_per_share=Decimal("5.0000"),
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        # TATN: только собрание — fallback-событие с полными условиями.
        tatn_meeting = ShareholderMeeting(
            ticker_id=tatn.id,
            meeting_date=TODAY + timedelta(days=6),
            meeting_type="annual",
            dividend_question=True,
            dividend_period="year",
            dividend_per_share=Decimal("15.0000"),
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        # MTSS: у собрания известен период, сумма — нет.
        mtss_meeting = ShareholderMeeting(
            ticker_id=mtss.id,
            meeting_date=TODAY + timedelta(days=12),
            meeting_type="extraordinary",
            dividend_question=True,
            dividend_period="half_year",
            dividend_per_share=None,
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        # SNGS: у собрания не известны ни период, ни сумма.
        sngs_meeting = ShareholderMeeting(
            ticker_id=sngs.id,
            meeting_date=TODAY + timedelta(days=20),
            meeting_type="annual",
            dividend_question=True,
            dividend_period=None,
            dividend_per_share=None,
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        # ROSN: только прошедшее собрание с дивидендным вопросом — past.
        rosn_meeting = ShareholderMeeting(
            ticker_id=rosn.id,
            meeting_date=TODAY - timedelta(days=20),
            meeting_type="annual",
            dividend_question=True,
            dividend_period="year",
            dividend_per_share=Decimal("3.0000"),
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        # PLZL: собрание без дивидендного вопроса событием не является.
        plzl_meeting = ShareholderMeeting(
            ticker_id=plzl.id,
            meeting_date=TODAY + timedelta(days=10),
            meeting_type="annual",
            dividend_question=False,
            dividend_period="year",
            dividend_per_share=Decimal("8.0000"),
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        # IRAO: прошедшая отсечка не мешает fallback на будущее собрание.
        irao_meeting = ShareholderMeeting(
            ticker_id=irao.id,
            meeting_date=TODAY + timedelta(days=9),
            meeting_type="annual",
            dividend_question=True,
            dividend_period="year",
            dividend_per_share=Decimal("1.0000"),
            source_url=SOURCE_URL,
            fetched_at=FETCHED_AT,
        )
        db_session.add_all(
            [
                sber_meeting,
                sber_far_meeting,
                lkoh_meeting,
                tatn_meeting,
                mtss_meeting,
                sngs_meeting,
                rosn_meeting,
                plzl_meeting,
                irao_meeting,
            ]
        )
        db_session.flush()

        db_session.add_all(
            [
                # SBER: две будущие отсечки — берётся ближайшая, связанная с собранием.
                RecordDate(
                    ticker_id=sber.id,
                    meeting_id=sber_meeting.id,
                    record_date=TODAY + timedelta(days=3),
                    kind="dividend_payment",
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
                RecordDate(
                    ticker_id=sber.id,
                    meeting_id=sber_far_meeting.id,
                    record_date=TODAY + timedelta(days=30),
                    kind="dividend_payment",
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
                # MGNT: отсечка сегодня — critical.
                RecordDate(
                    ticker_id=mgnt.id,
                    meeting_id=None,
                    record_date=TODAY,
                    kind="dividend_payment",
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
                # GAZP: только прошедшая отсечка — past.
                RecordDate(
                    ticker_id=gazp.id,
                    meeting_id=None,
                    record_date=TODAY - timedelta(days=10),
                    kind="dividend_payment",
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
                # Отсечка для участия в собрании статус не формирует.
                RecordDate(
                    ticker_id=aflt.id,
                    meeting_id=None,
                    record_date=TODAY + timedelta(days=5),
                    kind="meeting_participation",
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
                # LKOH вне сторожка — используется в тестах POST.
                RecordDate(
                    ticker_id=lkoh.id,
                    meeting_id=lkoh_meeting.id,
                    record_date=TODAY + timedelta(days=1),
                    kind="dividend_payment",
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
                # IRAO: прошедшая отсечка без связи с собранием.
                RecordDate(
                    ticker_id=irao.id,
                    meeting_id=None,
                    record_date=TODAY - timedelta(days=15),
                    kind="dividend_payment",
                    source_url=SOURCE_URL,
                    fetched_at=FETCHED_AT,
                ),
            ]
        )
        db_session.flush()

        db_session.add_all(
            [
                WatchlistItem(ticker_id=sber.id, threshold_days=7, created_at=FETCHED_AT),
                WatchlistItem(ticker_id=mgnt.id, threshold_days=7, created_at=FETCHED_AT),
                WatchlistItem(ticker_id=gazp.id, threshold_days=14, created_at=FETCHED_AT),
                WatchlistItem(ticker_id=aflt.id, threshold_days=7, created_at=FETCHED_AT),
                WatchlistItem(ticker_id=tatn.id, threshold_days=7, created_at=FETCHED_AT),
                WatchlistItem(ticker_id=mtss.id, threshold_days=7, created_at=FETCHED_AT),
                WatchlistItem(ticker_id=sngs.id, threshold_days=7, created_at=FETCHED_AT),
                WatchlistItem(ticker_id=rosn.id, threshold_days=7, created_at=FETCHED_AT),
                WatchlistItem(ticker_id=nvtk.id, threshold_days=7, created_at=FETCHED_AT),
                WatchlistItem(ticker_id=plzl.id, threshold_days=7, created_at=FETCHED_AT),
                WatchlistItem(ticker_id=irao.id, threshold_days=7, created_at=FETCHED_AT),
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


def test_list_watchlist_canonical_order(client: TestClient) -> None:
    """Порядок: датированные по событию, затем no_date, затем past."""
    response = client.get("/api/v1/watchlist")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 11
    assert [item["ticker"] for item in body["items"]] == [
        "MGNT",
        "SBER",
        "TATN",
        "IRAO",
        "MTSS",
        "SNGS",
        "AFLT",
        "NVTK",
        "PLZL",
        "GAZP",
        "ROSN",
    ]


def test_watchlist_dated_item_fields(client: TestClient) -> None:
    """Датированный сторожок: ближайшая отсечка, собрание, дни, статус, дивиденды."""
    body = client.get("/api/v1/watchlist").json()
    sber = next(item for item in body["items"] if item["ticker"] == "SBER")

    assert sber["short_name"] == "Сбербанк"
    assert sber["logo_url"] == "/static/logos/SBER.svg"
    assert sber["threshold_days"] == 7
    assert sber["created_at"] == "2026-10-21T12:00:00Z"
    assert sber["next_record_date"] == _iso(TODAY + timedelta(days=3))
    assert sber["next_meeting_date"] == _iso(TODAY + timedelta(days=2))
    assert sber["days_to_event"] == 3
    assert sber["status"] == "hot"
    assert sber["next_dividend"] == {
        "period": "year",
        "amount_per_share": 10.0,
        "yield_percent": 10.0,
    }
    assert sber["dsi"] == 85


def test_watchlist_critical_today(client: TestClient) -> None:
    """Отсечка сегодня — critical, days_to_event = 0, без собрания и условий."""
    body = client.get("/api/v1/watchlist").json()
    mgnt = body["items"][0]

    assert mgnt["ticker"] == "MGNT"
    assert mgnt["next_record_date"] == _iso(TODAY)
    assert mgnt["days_to_event"] == 0
    assert mgnt["status"] == "critical"
    assert mgnt["next_meeting_date"] is None
    assert mgnt["next_dividend"] is None
    assert mgnt["dsi"] is None


def test_watchlist_no_date_and_past(client: TestClient) -> None:
    """no_date (событий нет) и past (только прошедшие): даты и дни равны null."""
    body = client.get("/api/v1/watchlist").json()
    by_ticker = {item["ticker"]: item for item in body["items"]}

    for ticker in ("AFLT", "NVTK", "PLZL"):
        item = by_ticker[ticker]
        assert item["status"] == "no_date"
        assert item["next_record_date"] is None
        assert item["days_to_event"] is None
        assert item["next_meeting_date"] is None
        assert item["next_dividend"] is None

    gazp = by_ticker["GAZP"]
    assert gazp["status"] == "past"
    assert gazp["threshold_days"] == 14
    assert gazp["next_record_date"] is None
    assert gazp["days_to_event"] is None


def test_watchlist_past_by_meeting(client: TestClient) -> None:
    """Прошедшее собрание с дивидендным вопросом без будущих событий — past."""
    body = client.get("/api/v1/watchlist").json()
    rosn = next(item for item in body["items"] if item["ticker"] == "ROSN")

    assert rosn["status"] == "past"
    assert rosn["next_record_date"] is None
    assert rosn["next_meeting_date"] is None
    assert rosn["days_to_event"] is None
    assert rosn["next_dividend"] is None


def test_watchlist_fallback_to_meeting(client: TestClient) -> None:
    """Без будущей отсечки событием становится ближайшее собрание с дивидендным вопросом."""
    body = client.get("/api/v1/watchlist").json()
    tatn = next(item for item in body["items"] if item["ticker"] == "TATN")

    assert tatn["next_record_date"] == _iso(TODAY + timedelta(days=6))
    assert tatn["next_meeting_date"] == _iso(TODAY + timedelta(days=6))
    assert tatn["days_to_event"] == 6
    assert tatn["status"] == "hot"
    assert tatn["next_dividend"] == {
        "period": "year",
        "amount_per_share": 15.0,
        "yield_percent": 10.0,
    }


def test_watchlist_fallback_meeting_without_amount(client: TestClient) -> None:
    """Собрание без суммы: только период или вообще без условий."""
    body = client.get("/api/v1/watchlist").json()
    by_ticker = {item["ticker"]: item for item in body["items"]}

    mtss = by_ticker["MTSS"]
    assert mtss["next_record_date"] == _iso(TODAY + timedelta(days=12))
    assert mtss["next_meeting_date"] == _iso(TODAY + timedelta(days=12))
    assert mtss["status"] == "near"
    assert mtss["next_dividend"] == {
        "period": "half_year",
        "amount_per_share": None,
        "yield_percent": None,
    }

    sngs = by_ticker["SNGS"]
    assert sngs["next_record_date"] == _iso(TODAY + timedelta(days=20))
    assert sngs["status"] == "far"
    assert sngs["next_dividend"] is None


def test_watchlist_record_date_priority_over_meeting(client: TestClient) -> None:
    """Будущая отсечка приоритетнее собрания, даже если собрание наступает раньше."""
    body = client.get("/api/v1/watchlist").json()
    sber = next(item for item in body["items"] if item["ticker"] == "SBER")

    assert sber["next_record_date"] == _iso(TODAY + timedelta(days=3))
    assert sber["next_meeting_date"] == _iso(TODAY + timedelta(days=2))
    assert sber["days_to_event"] == 3
    assert sber["status"] == "hot"
    assert sber["next_dividend"]["amount_per_share"] == 10.0


def test_watchlist_past_cutoff_does_not_block_fallback(client: TestClient) -> None:
    """Прошедшая отсечка не мешает fallback на будущее собрание."""
    body = client.get("/api/v1/watchlist").json()
    irao = next(item for item in body["items"] if item["ticker"] == "IRAO")

    assert irao["next_record_date"] == _iso(TODAY + timedelta(days=9))
    assert irao["next_meeting_date"] == _iso(TODAY + timedelta(days=9))
    assert irao["days_to_event"] == 9
    assert irao["status"] == "near"
    assert irao["next_dividend"] == {
        "period": "year",
        "amount_per_share": 1.0,
        "yield_percent": 10.0,
    }


def test_watchlist_fallback_sorted_among_dated(client: TestClient) -> None:
    """Fallback-строки сортируются среди датированных по дате события."""
    body = client.get("/api/v1/watchlist").json()
    tickers = [item["ticker"] for item in body["items"]]

    assert tickers.index("SBER") < tickers.index("TATN")
    assert tickers.index("TATN") < tickers.index("IRAO")
    assert tickers.index("IRAO") < tickers.index("MTSS")
    assert tickers.index("MTSS") < tickers.index("SNGS")
    # Датированные идут выше no_date, а no_date — выше past.
    assert tickers.index("SNGS") < tickers.index("AFLT")
    assert tickers.index("PLZL") < tickers.index("GAZP")


def test_watchlist_pagination(client: TestClient) -> None:
    """Пагинация применяется после сортировки; total — общее число сторожков."""
    first = client.get("/api/v1/watchlist", params={"page": 1, "page_size": 2}).json()
    second = client.get("/api/v1/watchlist", params={"page": 2, "page_size": 2}).json()

    assert first["total"] == 11
    assert [item["ticker"] for item in first["items"]] == ["MGNT", "SBER"]
    assert second["total"] == 11
    assert [item["ticker"] for item in second["items"]] == ["TATN", "IRAO"]


def test_create_watchlist_item(client: TestClient) -> None:
    """Новый тикер — 201, threshold_days по умолчанию из конфигурации."""
    response = client.post("/api/v1/watchlist", json={"ticker": "lkoh"})

    assert response.status_code == 201
    body = response.json()
    assert body["ticker"] == "LKOH"
    assert body["threshold_days"] == 7
    assert body["next_record_date"] == _iso(TODAY + timedelta(days=1))
    assert body["next_meeting_date"] == _iso(TODAY + timedelta(days=1))
    assert body["days_to_event"] == 1
    assert body["status"] == "hot"
    assert body["next_dividend"] == {
        "period": "quarter",
        "amount_per_share": 5.0,
        "yield_percent": 10.0,
    }


def test_create_watchlist_item_with_threshold(client: TestClient) -> None:
    """Переданный threshold_days сохраняется при создании."""
    response = client.post(
        "/api/v1/watchlist", json={"ticker": "lkoh", "threshold_days": 30}
    )

    assert response.status_code == 201
    assert response.json()["threshold_days"] == 30
    assert response.json()["status"] == "hot"


def test_create_existing_item_is_idempotent(client: TestClient) -> None:
    """Повторный POST не создаёт дубль: 200, threshold_days обновляется."""
    response = client.post(
        "/api/v1/watchlist", json={"ticker": "SBER", "threshold_days": 10}
    )

    assert response.status_code == 200
    assert response.json()["threshold_days"] == 10

    body = client.get("/api/v1/watchlist").json()
    assert body["total"] == 11
    assert sum(1 for item in body["items"] if item["ticker"] == "SBER") == 1


def test_create_existing_fallback_item_returns_meeting_event(client: TestClient) -> None:
    """Повторный POST для fallback-сторожка отдаёт собрание как событие."""
    response = client.post("/api/v1/watchlist", json={"ticker": "TATN"})

    assert response.status_code == 200
    body = response.json()
    assert body["next_record_date"] == _iso(TODAY + timedelta(days=6))
    assert body["next_meeting_date"] == _iso(TODAY + timedelta(days=6))
    assert body["next_dividend"]["amount_per_share"] == 15.0


def test_create_existing_item_without_threshold_keeps_value(client: TestClient) -> None:
    """Без threshold_days существующее значение не меняется."""
    response = client.post("/api/v1/watchlist", json={"ticker": "GAZP"})

    assert response.status_code == 200
    assert response.json()["threshold_days"] == 14


def test_create_normalizes_ticker(client: TestClient) -> None:
    """Тикер в теле нормализуется (trim, верхний регистр)."""
    response = client.post("/api/v1/watchlist", json={"ticker": "  lkoh "})

    assert response.status_code == 201
    assert response.json()["ticker"] == "LKOH"


def test_create_unknown_ticker(client: TestClient) -> None:
    """Неизвестный тикер — 404 по контракту."""
    response = client.post("/api/v1/watchlist", json={"ticker": "YNDX"})

    assert response.status_code == 404
    assert response.json() == {"detail": "ticker not found"}


@pytest.mark.parametrize(
    "payload",
    [
        {"ticker": "SBER", "threshold_days": 0},
        {"ticker": "SBER", "threshold_days": 366},
        {"ticker": ""},
        {"ticker": "   "},
        {},
    ],
)
def test_create_validation_errors(client: TestClient, payload: dict) -> None:
    """Невалидное тело — 422 (автовалидация Pydantic)."""
    response = client.post("/api/v1/watchlist", json=payload)

    assert response.status_code == 422


def test_delete_watchlist_item(client: TestClient) -> None:
    """Удаление по SECID регистронезависимо: 204 без тела."""
    response = client.delete("/api/v1/watchlist/sber")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/api/v1/watchlist").json()["total"] == 10


def test_delete_missing_watchlist_item(client: TestClient) -> None:
    """Сторожка для существующего тикера нет — 404."""
    response = client.delete("/api/v1/watchlist/LKOH")

    assert response.status_code == 404
    assert response.json() == {"detail": "watchlist item not found"}


def test_delete_unknown_ticker(client: TestClient) -> None:
    """Неизвестный тикер — 404."""
    response = client.delete("/api/v1/watchlist/YNDX")

    assert response.status_code == 404
    assert response.json() == {"detail": "watchlist item not found"}


@pytest.mark.parametrize(
    ("next_record_date", "threshold_days", "expected"),
    [
        (date(2026, 10, 19), 7, "critical"),
        (date(2026, 10, 20), 7, "hot"),
        (date(2026, 10, 26), 7, "hot"),
        (date(2026, 10, 27), 7, "near"),
        (date(2026, 11, 2), 7, "near"),
        (date(2026, 11, 3), 7, "far"),
        (None, 7, "no_date"),
    ],
)
def test_calc_status_boundaries(
    next_record_date: date | None, threshold_days: int, expected: str
) -> None:
    """Границы шкалы из спецификации: T = 7, S = 14 (пример 2026-10-19)."""
    # Для no_date прошедших дат нет; отдельный кейс past проверяется ниже.
    assert (
        calc_status(
            date(2026, 10, 19), threshold_days, 14, next_record_date, has_past_events=False
        )
        == expected
    )


def test_calc_status_past_without_future_dates() -> None:
    """Будущих дат нет, прошедшие есть — past."""
    assert calc_status(date(2026, 10, 19), 7, 14, None, has_past_events=True) == "past"


def test_calc_days_to_event() -> None:
    """Дни до даты события считаются от текущей даты; без даты — None."""
    today = date(2026, 10, 19)
    assert calc_days_to_event(today, date(2026, 10, 19)) == 0
    assert calc_days_to_event(today, date(2026, 10, 26)) == 7
    assert calc_days_to_event(today, None) is None
