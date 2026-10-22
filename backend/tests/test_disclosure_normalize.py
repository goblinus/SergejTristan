"""Тесты сопоставления сообщений disclosure с тикерами и нормализации."""

from datetime import UTC, date, datetime
from decimal import Decimal

from scripts.ingestion.normalize import (
    TickerRef,
    match_tickers,
    normalize_disclosure_messages,
)
from scripts.ingestion.parsers.disclosure_events import DisclosureMessageFact

FETCHED_AT = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)

SBER = TickerRef("SBER", "Сбербанк", "Сбербанк России ПАО ао", "RU0009029540")
SBERP = TickerRef("SBERP", "Сбербанк-п", "Сбербанк России ПАО ап", "RU0009029557")
GAZP = TickerRef("GAZP", "Газпром", "Газпром ПАО ао", "RU0007661625")


def _fact(
    *,
    kind: str = "meeting",
    issuer: str | None = "ПАО Сбербанк",
    text: str = "",
    meeting_date: date | None = date(2026, 6, 30),
    meeting_type: str | None = "annual",
    dividend_question: bool = True,
    period: str | None = None,
    amount: Decimal | None = None,
    record_date: date | None = None,
    record_date_kind: str | None = None,
    description: str | None = None,
    isins: tuple[str, ...] = (),
    url: str = "https://example.test/message",
) -> DisclosureMessageFact:
    return DisclosureMessageFact(
        url=url,
        title="Сообщение",
        issuer_name=issuer,
        inn=None,
        published_at=datetime(2026, 10, 21),
        message_type="Сообщение",
        message_kind=kind,
        text=text,
        meeting_date=meeting_date,
        meeting_type=meeting_type,
        dividend_question=dividend_question,
        dividend_period=period,
        dividend_per_share=amount,
        record_date=record_date,
        record_date_kind=record_date_kind,
        description=description,
        isins=isins,
    )


def test_match_by_isin() -> None:
    """ISIN в тексте сообщения — самый надёжный признак тикера."""
    fact = _fact(issuer="Неизвестное наименование", isins=("RU0009029540",))

    assert match_tickers(fact, [SBER, SBERP, GAZP]) == [SBER]


def test_non_matching_isin_does_not_fall_back_to_name() -> None:
    """ISIN облигации не должен сопоставлять сообщение с акцией по имени эмитента."""
    fact = _fact(issuer="ПАО Сбербанк", isins=("RU000A10CTT4",))

    assert match_tickers(fact, [SBER]) == []


def test_match_by_full_name_with_legal_form() -> None:
    """Полное наименование с организационно-правовой формой сопоставляется."""
    fact = _fact(issuer="Публичное акционерное общество «Сбербанк России»", text="")

    assert match_tickers(fact, [SBER, GAZP]) == [SBER]


def test_match_by_short_name() -> None:
    """Краткое наименование с ПАО сопоставляется с тикером."""
    fact = _fact(issuer="ПАО Газпром")

    assert match_tickers(fact, [SBER, GAZP]) == [GAZP]


def test_unknown_issuer_is_not_matched() -> None:
    """Неизвестный эмитент не даёт ложного совпадения."""
    fact = _fact(issuer="ПАО Совершенно другая компания")

    assert match_tickers(fact, [SBER, GAZP]) == []


def test_class_filter_selects_preferred() -> None:
    """Если сообщение только о привилегированных акциях, обыкновенный тикер отсекается."""
    fact = _fact(
        issuer="ПАО Сбербанк",
        text="Выплатить дивиденды по привилегированным акциям",
    )

    assert match_tickers(fact, [SBER, SBERP]) == [SBERP]


def test_normalize_merges_announcement_and_results() -> None:
    """Объявление и итоги одного собрания объединяются, условия не теряются."""
    announcement = _fact(
        description="Повестка: о выплате дивидендов",
        url="https://example.test/announcement",
    )
    results = _fact(
        kind="results",
        period="year",
        amount=Decimal("37.64"),
        description="Выплатить дивиденды за 2025 год в размере 37,64 руб. на одну акцию",
        url="https://example.test/results",
    )

    normalized = normalize_disclosure_messages(
        [announcement, results], [SBER], fetched_at=FETCHED_AT
    )

    assert len(normalized.meetings) == 1
    meeting = normalized.meetings[0]
    assert meeting.ticker == "SBER"
    assert meeting.dividend_period == "year"
    assert meeting.dividend_per_share == Decimal("37.64")
    assert "37,64" in (meeting.description or "")


def test_normalize_keeps_meeting_and_dividend_record_date() -> None:
    """Итоги собрания дают и собрание, и связанную дату выплаты дивидендов."""
    fact = _fact(
        kind="results",
        period="year",
        amount=Decimal("37.64"),
        record_date=date(2026, 7, 20),
        record_date_kind="dividend_payment",
    )

    normalized = normalize_disclosure_messages([fact], [SBER], fetched_at=FETCHED_AT)

    assert len(normalized.meetings) == 1
    assert len(normalized.record_dates) == 1
    record_date = normalized.record_dates[0]
    assert record_date.kind == "dividend_payment"
    assert record_date.record_date == date(2026, 7, 20)
    assert record_date.meeting_date == date(2026, 6, 30)
    assert record_date.meeting_type == "annual"


def test_normalize_links_standalone_record_date() -> None:
    """Отдельная отсечка связывается с ближайшим собранием по эвристике."""
    meeting = _fact(
        meeting_date=date(2026, 11, 20),
        meeting_type="extraordinary",
    )
    record_date = _fact(
        kind="record_date",
        issuer="ПАО Сбербанк",
        meeting_date=None,
        meeting_type=None,
        dividend_question=False,
        record_date=date(2026, 10, 27),
        record_date_kind="meeting_participation",
        url="https://example.test/record-date",
    )

    normalized = normalize_disclosure_messages(
        [meeting, record_date], [SBER], fetched_at=FETCHED_AT
    )

    assert len(normalized.record_dates) == 1
    linked = normalized.record_dates[0]
    assert linked.meeting_date == date(2026, 11, 20)
    assert linked.meeting_type == "extraordinary"


def test_normalize_prefers_meeting_with_matching_period() -> None:
    """Эвристика связывания предпочитает собрание с тем же периодом выплаты."""
    quarter = _fact(
        meeting_date=date(2026, 7, 10),
        meeting_type="extraordinary",
        period="quarter",
        url="https://example.test/quarter",
    )
    annual = _fact(
        meeting_date=date(2026, 6, 30),
        meeting_type="annual",
        period="year",
        url="https://example.test/annual",
    )
    record_date = _fact(
        kind="record_date",
        meeting_date=None,
        meeting_type=None,
        dividend_question=False,
        period="year",
        record_date=date(2026, 7, 20),
        record_date_kind="dividend_payment",
        url="https://example.test/record-date",
    )

    normalized = normalize_disclosure_messages(
        [quarter, annual, record_date], [SBER], fetched_at=FETCHED_AT
    )

    assert len(normalized.record_dates) == 1
    linked = normalized.record_dates[0]
    assert linked.meeting_date == date(2026, 6, 30)
    assert linked.meeting_type == "annual"


def test_non_dividend_meeting_is_skipped() -> None:
    """Собрание без вопроса о дивидендах не попадает в результат."""
    fact = _fact(dividend_question=False)

    normalized = normalize_disclosure_messages([fact], [SBER], fetched_at=FETCHED_AT)

    assert normalized.meetings == []
    assert normalized.skipped == 1


def test_meeting_without_date_is_skipped() -> None:
    """Собрание без распознанной даты отбрасывается с учётом в skipped."""
    fact = _fact(meeting_date=None)

    normalized = normalize_disclosure_messages([fact], [SBER], fetched_at=FETCHED_AT)

    assert normalized.meetings == []
    assert normalized.skipped == 1
