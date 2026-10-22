"""Тесты загрузчика собраний и дат отсечки: идемпотентность и связывание."""

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, RecordDate, ShareholderMeeting, Ticker
from scripts.ingestion.loader import load_meetings, load_record_dates
from scripts.ingestion.normalize import NormalizedMeeting, NormalizedRecordDate

FETCHED_AT = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
SOURCE_URL = "https://www.disclosure.ru/rus/corpnews/news.shtml?newsisn=1"


@pytest.fixture()
def session() -> Iterator[Session]:
    """Временная SQLite в памяти с одним активным тикером."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as db_session:
        db_session.add(
            Ticker(
                ticker="SBER",
                short_name="Сбербанк",
                isin="RU0009029540",
                is_active=True,
                source_url="https://iss.moex.com/iss/example.json",
                fetched_at=FETCHED_AT,
            )
        )
        db_session.commit()
        yield db_session

    engine.dispose()


def _meeting(
    *,
    ticker: str = "SBER",
    meeting_date: date = date(2026, 6, 30),
    meeting_type: str = "annual",
    period: str | None = None,
    amount: Decimal | None = None,
    description: str | None = None,
    source_url: str = SOURCE_URL,
) -> NormalizedMeeting:
    return NormalizedMeeting(
        ticker=ticker,
        meeting_date=meeting_date,
        meeting_type=meeting_type,
        dividend_question=True,
        dividend_period=period,
        dividend_per_share=amount,
        description=description,
        source_url=source_url,
        fetched_at=FETCHED_AT,
    )


def _record_date(
    *,
    record_date: date = date(2026, 7, 20),
    kind: str = "dividend_payment",
    meeting_date: date | None = None,
    meeting_type: str | None = None,
    dividend_period: str | None = None,
    source_url: str = SOURCE_URL,
) -> NormalizedRecordDate:
    return NormalizedRecordDate(
        ticker="SBER",
        record_date=record_date,
        kind=kind,
        meeting_date=meeting_date,
        meeting_type=meeting_type,
        dividend_period=dividend_period,
        source_url=source_url,
        fetched_at=FETCHED_AT,
    )


def test_load_meetings_inserts(session: Session) -> None:
    """Первая загрузка вставляет собрание с дивидендными условиями."""
    stats = load_meetings(
        session,
        [
            _meeting(
                period="year",
                amount=Decimal("37.64"),
                description="О выплате дивидендов",
            )
        ],
    )
    session.commit()

    row = session.execute(select(ShareholderMeeting)).scalar_one()
    assert stats.inserted == 1
    assert stats.updated == 0
    assert row.meeting_date == date(2026, 6, 30)
    assert row.meeting_type == "annual"
    assert row.dividend_period == "year"
    assert row.dividend_per_share == Decimal("37.64")
    assert row.description == "О выплате дивидендов"


def test_load_meetings_is_idempotent_and_preserves_terms(session: Session) -> None:
    """Повторный upsert не создаёт дубль и не затирает уже раскрытые условия."""
    load_meetings(session, [_meeting(description="Объявление собрания")])
    load_meetings(
        session,
        [
            _meeting(
                period="year",
                amount=Decimal("37.64"),
                description="О выплате дивидендов за 2025 год",
            )
        ],
    )
    stats = load_meetings(session, [_meeting(description="Объявление собрания")])
    session.commit()

    row = session.execute(select(ShareholderMeeting)).scalar_one()
    assert stats.inserted == 0
    assert stats.updated == 1
    assert row.dividend_period == "year"
    assert row.dividend_per_share == Decimal("37.64")
    assert row.description == "О выплате дивидендов за 2025 год"


def test_load_meetings_merges_duplicates_in_one_call(session: Session) -> None:
    """Дубли в одной пачке объединяются, непустые поля сохраняются."""
    load_meetings(
        session,
        [
            _meeting(description="Коротко"),
            _meeting(period="quarter", amount=Decimal("1.50"), description="Подробно"),
        ],
    )
    session.commit()

    row = session.execute(select(ShareholderMeeting)).scalar_one()
    assert row.dividend_period == "quarter"
    assert row.dividend_per_share == Decimal("1.50")
    assert row.description == "Подробно"


def test_load_meetings_skips_unknown_ticker(session: Session) -> None:
    """Собрание неизвестного/неактивного тикера отбрасывается."""
    stats = load_meetings(session, [_meeting(ticker="UNKNOWN")])
    session.commit()

    assert stats.skipped == 1
    assert stats.inserted == 0
    assert session.execute(select(ShareholderMeeting)).scalar_one_or_none() is None


def test_load_record_dates_links_meeting(session: Session) -> None:
    """Отсечка связывается с собранием по эмитенту и дате собрания."""
    load_meetings(session, [_meeting()])
    session.flush()

    stats = load_record_dates(
        session,
        [_record_date(meeting_date=date(2026, 6, 30), meeting_type="annual")],
    )
    session.commit()

    meeting = session.execute(select(ShareholderMeeting)).scalar_one()
    record_date = session.execute(select(RecordDate)).scalar_one()
    assert stats.inserted == 1
    assert record_date.meeting_id == meeting.id
    assert record_date.kind == "dividend_payment"


def test_load_record_dates_links_meeting_from_previous_run(session: Session) -> None:
    """Отсечка без ссылки связывается с уже сохранённым собранием по близости дат."""
    load_meetings(session, [_meeting()])
    session.flush()

    stats = load_record_dates(session, [_record_date()])
    session.commit()

    meeting = session.execute(select(ShareholderMeeting)).scalar_one()
    record_date = session.execute(select(RecordDate)).scalar_one()
    assert stats.inserted == 1
    assert record_date.meeting_id == meeting.id


def test_load_record_dates_prefers_matching_period(session: Session) -> None:
    """При выборе собрания приоритет у совпадающего периода выплаты."""
    load_meetings(
        session,
        [
            _meeting(
                meeting_date=date(2026, 7, 10),
                meeting_type="extraordinary",
                period="quarter",
            ),
            _meeting(
                meeting_date=date(2026, 6, 30),
                meeting_type="annual",
                period="year",
            ),
        ],
    )
    session.flush()

    load_record_dates(
        session, [_record_date(record_date=date(2026, 7, 20), dividend_period="year")]
    )
    session.commit()

    annual = session.execute(
        select(ShareholderMeeting).where(ShareholderMeeting.meeting_type == "annual")
    ).scalar_one()
    record_date = session.execute(select(RecordDate)).scalar_one()
    assert record_date.meeting_id == annual.id


def test_load_record_dates_ambiguous_meeting_not_linked(session: Session) -> None:
    """При двух равноудалённых собраниях связь не ставится."""
    load_meetings(
        session,
        [
            _meeting(meeting_date=date(2026, 6, 30), meeting_type="annual"),
            _meeting(meeting_date=date(2026, 6, 30), meeting_type="extraordinary"),
        ],
    )
    session.flush()

    load_record_dates(session, [_record_date(record_date=date(2026, 7, 20))])
    session.commit()

    record_date = session.execute(select(RecordDate)).scalar_one()
    assert record_date.meeting_id is None


def test_load_record_dates_without_meeting(session: Session) -> None:
    """Отсечка без собрания сохраняется с meeting_id = NULL."""
    stats = load_record_dates(session, [_record_date()])
    session.commit()

    record_date = session.execute(select(RecordDate)).scalar_one()
    assert stats.inserted == 1
    assert record_date.meeting_id is None


def test_load_record_dates_is_idempotent(session: Session) -> None:
    """Повторный upsert не создаёт дубль отсечки."""
    load_record_dates(session, [_record_date()])
    stats = load_record_dates(session, [_record_date()])
    session.commit()

    rows = list(session.execute(select(RecordDate)).scalars())
    assert stats.inserted == 0
    assert stats.updated == 1
    assert len(rows) == 1


def test_load_record_dates_preserves_existing_meeting_link(session: Session) -> None:
    """Повторная запись без ссылки на собрание не сбрасывает установленную связь."""
    load_meetings(session, [_meeting()])
    session.flush()
    load_record_dates(
        session,
        [_record_date(meeting_date=date(2026, 6, 30), meeting_type="annual")],
    )
    load_record_dates(session, [_record_date()])
    session.commit()

    record_date = session.execute(select(RecordDate)).scalar_one()
    assert record_date.meeting_id is not None


def test_load_record_dates_skips_unknown_ticker(session: Session) -> None:
    """Отсечка неизвестного тикера отбрасывается."""
    unknown = NormalizedRecordDate(
        ticker="UNKNOWN",
        record_date=date(2026, 7, 20),
        kind="dividend_payment",
        source_url=SOURCE_URL,
        fetched_at=FETCHED_AT,
    )
    stats = load_record_dates(session, [unknown])
    session.commit()

    assert stats.skipped == 1
    assert session.execute(select(RecordDate)).scalar_one_or_none() is None
