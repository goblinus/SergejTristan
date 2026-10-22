"""Тесты оркестрации скрипта fetch_meetings_disclosure без сети."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import scripts.fetch_meetings_disclosure as script
from app.models import Base, RecordDate, ShareholderMeeting, Ticker
from scripts.ingestion.parsers.disclosure_events import DisclosureFeedItem
from scripts.ingestion.sources.common import SourceError

FIXTURES = Path(__file__).parent / "fixtures"
FETCHED_AT = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
RESULTS_TYPE = "Решения общих собраний участников (акционеров)"


def _html(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("cp1251", errors="replace")


def _item(url: str = "https://example.test/results") -> DisclosureFeedItem:
    return DisclosureFeedItem(
        url=url,
        title=f"ПАО Сбербанк - {RESULTS_TYPE}",
        issuer_name="ПАО Сбербанк",
        published_at=datetime(2026, 10, 21, 12, 0),
        message_type=RESULTS_TYPE,
    )


@pytest.fixture()
def factory() -> Iterator[sessionmaker]:
    """Фабрика сессий на временной SQLite с активным тикером SBER."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        session.add(
            Ticker(
                ticker="SBER",
                short_name="Сбербанк",
                full_name="Сбербанк России ПАО ао",
                isin="RU0009029540",
                is_active=True,
                source_url="https://iss.moex.com/iss/example.json",
                fetched_at=FETCHED_AT,
            )
        )
        session.commit()
    yield session_factory
    engine.dispose()


def _fake_source(*, fail_feed: bool = False, fail_message: bool = False):
    def fetch_feed(_client, _settings, _lookback_days):
        if fail_feed:
            raise SourceError("source unavailable")
        return [_item()]

    def fetch_message(_client, _item, _settings):
        if fail_message:
            raise SourceError("message unavailable")
        return _html("disclosure_results.html")

    return SimpleNamespace(fetch_feed=fetch_feed, fetch_message=fetch_message)


def test_main_writes_meetings_and_record_dates(factory, monkeypatch, capsys) -> None:
    """Полный пайплайн сохраняет собрание и связанную дату отсечки."""
    monkeypatch.setattr(script, "SessionLocal", factory)
    monkeypatch.setitem(script.SOURCE_MODULES, "disclosure", _fake_source())

    code = script.main(["--source", "disclosure"])

    assert code == 0
    with factory() as session:
        meeting = session.execute(select(ShareholderMeeting)).scalar_one()
        record_date = session.execute(select(RecordDate)).scalar_one()
        assert meeting.meeting_date.isoformat() == "2026-06-30"
        assert meeting.dividend_period == "year"
        assert meeting.dividend_per_share == Decimal("37.64")
        assert record_date.record_date.isoformat() == "2026-07-20"
        assert record_date.meeting_id == meeting.id


def test_dry_run_does_not_write(factory, monkeypatch) -> None:
    """--dry-run проходит пайплайн, но не пишет в БД."""
    monkeypatch.setattr(script, "SessionLocal", factory)
    monkeypatch.setitem(script.SOURCE_MODULES, "disclosure", _fake_source())

    code = script.main(["--source", "disclosure", "--dry-run"])

    assert code == 0
    with factory() as session:
        assert session.execute(select(ShareholderMeeting)).scalar_one_or_none() is None
        assert session.execute(select(RecordDate)).scalar_one_or_none() is None


def test_message_failure_returns_partial_code(factory, monkeypatch) -> None:
    """Ошибка загрузки сообщения — частичный сбой с кодом 2."""
    monkeypatch.setattr(script, "SessionLocal", factory)
    monkeypatch.setitem(
        script.SOURCE_MODULES, "disclosure", _fake_source(fail_message=True)
    )

    code = script.main(["--source", "disclosure"])

    assert code == 2


def test_all_sources_unavailable_returns_fatal_code(factory, monkeypatch) -> None:
    """Недоступность всех источников — код 1."""
    monkeypatch.setattr(script, "SessionLocal", factory)
    monkeypatch.setitem(
        script.SOURCE_MODULES, "disclosure", _fake_source(fail_feed=True)
    )
    monkeypatch.setitem(
        script.SOURCE_MODULES, "e-disclosure", _fake_source(fail_feed=True)
    )

    code = script.main([])

    assert code == 1


def test_reserve_source_is_used_when_primary_fails(factory, monkeypatch) -> None:
    """При сбое основного источника используется резервный."""
    monkeypatch.setattr(script, "SessionLocal", factory)
    monkeypatch.setitem(
        script.SOURCE_MODULES, "disclosure", _fake_source(fail_feed=True)
    )
    monkeypatch.setitem(script.SOURCE_MODULES, "e-disclosure", _fake_source())

    code = script.main([])

    assert code == 0
    with factory() as session:
        assert session.execute(select(ShareholderMeeting)).scalar_one_or_none() is not None
