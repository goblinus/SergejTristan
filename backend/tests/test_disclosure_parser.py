"""Тесты парсера сообщений disclosure на сохранённых страницах источников."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from scripts.ingestion.parsers.disclosure_events import (
    DisclosureFeedItem,
    is_candidate_message_type,
    parse_disclosure_feed_page,
    parse_edisclosure_feed_page,
    parse_message,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _html(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("cp1251", errors="replace")


def _feed_item(message_type: str, issuer: str = "Эмитент") -> DisclosureFeedItem:
    return DisclosureFeedItem(
        url="https://example.test/message",
        title=f"{issuer} - {message_type}",
        issuer_name=issuer,
        published_at=datetime(2026, 10, 21, 12, 0),
        message_type=message_type,
    )


def test_parse_disclosure_feed_page() -> None:
    """Лента АК&М: 20 сообщений, курсор следующей страницы и поля записи."""
    page = parse_disclosure_feed_page(_html("disclosure_feed.html"))

    assert len(page.items) == 20
    assert page.next_cursor == "20261021182505"

    first = page.items[0]
    assert first.published_at == datetime(2026, 10, 21, 19, 49)
    assert first.issuer_name == 'ООО "АСГ ТРАНСФОРМАТОРЕН"'
    assert first.message_type == "Выплаченные доходы по эмиссионным ценным бумагам эмитента"
    assert "newsisn=9479915" in first.url


def test_parse_edisclosure_feed_page() -> None:
    """Лента зеркала Интерфакса: сообщения и абсолютные ссылки."""
    page = parse_edisclosure_feed_page(_html("edisclosure_feed.html"))

    assert len(page.items) == 50
    first = page.items[0]
    assert first.published_at == datetime(2026, 10, 21, 19, 47, 10)
    assert first.issuer_name == "Общество с ограниченной ответственностью «АСГ ТРАНСФОРМАТОРЕН»"
    assert first.message_type == (
        "Выплаченные доходы или иные выплаты, причитающиеся владельцам ценных бумаг эмитента"
    )
    assert first.url.startswith("https://disclosure.1prime.ru/news/-12/")


def test_parse_meeting_message() -> None:
    """Объявление собрания: дата, тип, дата участия, ИНН, повестка."""
    fact = parse_message(
        _html("disclosure_meeting.html"),
        _feed_item(
            "Проведение общего собрания акционеров акционерного общества", 'АО "Сокол"'
        ),
    )

    assert fact is not None
    assert fact.message_kind == "meeting"
    assert fact.issuer_name == 'Акционерное общество "Сокол"'
    assert fact.inn == "7718059412"
    assert fact.meeting_date == date(2026, 11, 20)
    assert fact.meeting_type == "extraordinary"
    assert fact.record_date == date(2026, 10, 27)
    assert fact.record_date_kind == "meeting_participation"
    assert fact.dividend_question is False
    assert fact.dividend_period is None
    assert fact.dividend_per_share is None
    assert "Утверждение распределения прибыли" in (fact.description or "")


def test_parse_results_message() -> None:
    """Итоги собрания: дивиденды, период, сумма и дата выплаты."""
    fact = parse_message(
        _html("disclosure_results.html"),
        _feed_item("Решения общих собраний участников (акционеров)", "ПАО Сбербанк"),
    )

    assert fact is not None
    assert fact.message_kind == "results"
    assert fact.issuer_name == "Публичное акционерное общество «Сбербанк России»"
    assert fact.inn == "7707083893"
    assert fact.meeting_date == date(2026, 6, 30)
    assert fact.meeting_type == "annual"
    assert fact.dividend_question is True
    assert fact.dividend_period == "year"
    assert fact.dividend_per_share == Decimal("37.64")
    assert fact.record_date == date(2026, 7, 20)
    assert fact.record_date_kind == "dividend_payment"
    assert "RU0009029540" in fact.isins
    assert "Выплатить дивиденды" in (fact.description or "")


def test_parse_record_date_message() -> None:
    """Отдельное сообщение о дате отсечки: дата, вид и ISIN для связывания."""
    fact = parse_message(
        _html("disclosure_record_date.html"),
        _feed_item(
            "Дата, на которую определяются лица, имеющие право на осуществление прав"
            " по именным эмиссионным ценным бумагам",
            "ПАО ММЗ Рассвет",
        ),
    )

    assert fact is not None
    assert fact.message_kind == "record_date"
    assert fact.inn == "7703010005"
    assert fact.record_date == date(2026, 11, 1)
    assert fact.record_date_kind == "meeting_participation"
    assert fact.isins == ("RU000A0JQ9R5",)


def test_parse_ballot_meeting_uses_ballot_deadline() -> None:
    """Для заочного собрания дата собрания — дата окончания приёма бюллетеней."""
    fact = parse_message(
        _html("disclosure_meeting_ballot.html"),
        _feed_item(
            "Созыв общего собрания участников (акционеров)", 'ПАО "ММЗ "Рассвет"'
        ),
    )

    assert fact is not None
    assert fact.meeting_date == date(2026, 11, 25)
    assert fact.meeting_type == "extraordinary"
    assert fact.record_date == date(2026, 11, 1)
    assert fact.record_date_kind == "meeting_participation"
    assert fact.dividend_question is False


def test_parse_akm_record_date_message() -> None:
    """Формат АК&М «Дата определения (фиксации) лиц...»."""
    fact = parse_message(
        _html("disclosure_record_date_akm.html"),
        _feed_item(
            "Дата определения (фиксации) лиц, имеющих право на осуществление"
            " прав по ценным бумагам эмитента",
            'АО "Экспобанк"',
        ),
    )

    assert fact is not None
    assert fact.record_date == date(2026, 10, 26)
    assert fact.record_date_kind == "meeting_participation"


def test_parse_record_date_with_explanation_in_value() -> None:
    """Дата может стоять в конце пояснения в поле 2.3."""
    fact = parse_message(
        _html("disclosure_record_date_explained.html"),
        _feed_item(
            "Дата определения (фиксации) лиц, имеющих право на осуществление"
            " прав по ценным бумагам эмитента",
            'АО "Уралэлектромедь"',
        ),
    )

    assert fact is not None
    assert fact.record_date == date(2026, 11, 1)
    # Упоминание дивидендов в правах по акциям не делает отсечку дивидендной.
    assert fact.record_date_kind == "meeting_participation"


@pytest.mark.parametrize(
    ("fixture", "issuer", "meeting_date", "meeting_type"),
    [
        (
            "disclosure_meeting_hnfg.html",
            "ПАО Хендерсон Фэшн Групп",
            date(2026, 11, 20),
            "extraordinary",
        ),
        (
            "disclosure_meeting_samaraenergo.html",
            "ПАО Самараэнерго",
            date(2026, 11, 19),
            "extraordinary",
        ),
        (
            "disclosure_meeting_kuazot.html",
            "ПАО КуйбышевАзот",
            date(2026, 11, 20),
            "extraordinary",
        ),
        (
            "disclosure_meeting_cian.html",
            "МКПАО Циан",
            date(2026, 11, 19),
            "extraordinary",
        ),
    ],
)
def test_parse_meeting_date_format_variants(
    fixture: str, issuer: str, meeting_date: date, meeting_type: str
) -> None:
    """Дата собрания в разных формулировках, включая дату окончания бюллетеней."""
    fact = parse_message(
        _html(fixture),
        _feed_item("Созыв общего собрания участников (акционеров)", issuer),
    )

    assert fact is not None
    assert fact.meeting_date == meeting_date
    assert fact.meeting_type == meeting_type
    assert fact.record_date is not None
    assert fact.record_date_kind == "meeting_participation"


def test_parse_integer_dividend_amount() -> None:
    """Сумма на акцию может быть целым числом рублей."""
    fact = parse_message(
        _html("disclosure_meeting_hnfg.html"),
        _feed_item(
            "Созыв общего собрания участников (акционеров)",
            "ПАО Хендерсон Фэшн Групп",
        ),
    )

    assert fact is not None
    assert fact.dividend_question is True
    assert fact.dividend_period == "quarter"
    assert fact.dividend_per_share == Decimal("8")


def test_parse_fractional_dividend_per_each_share() -> None:
    """Сумма может быть указана «на каждую акцию», а не «на одну»."""
    fact = parse_message(
        _html("disclosure_meeting_samaraenergo.html"),
        _feed_item(
            "Созыв общего собрания участников (акционеров)", "ПАО Самараэнерго"
        ),
    )

    assert fact is not None
    assert fact.dividend_per_share == Decimal("0.42")


def test_non_calendar_message_returns_none() -> None:
    """Сообщение другого типа не разбирается как сущфакт календаря."""
    fact = parse_message(
        _html("disclosure_results.html"),
        _feed_item("Погашение облигаций", "ПАО Сбербанк"),
    )

    assert fact is None


@pytest.mark.parametrize(
    ("message_type", "expected"),
    [
        ("Проведение общего собрания акционеров акционерного общества", True),
        (
            "Информация о проведении общего собрания акционеров акционерного общества",
            True,
        ),
        ("Решения общих собраний участников (акционеров)", True),
        (
            "Дата, на которую определяются лица, имеющие право на осуществление прав"
            " по именным эмиссионным ценным бумагам",
            True,
        ),
        ("Погашение облигаций", False),
        ("Выплаченные доходы по эмиссионным ценным бумагам эмитента", False),
    ],
)
def test_is_candidate_message_type(message_type: str, expected: bool) -> None:
    """Фильтр типов сообщений ленты."""
    assert is_candidate_message_type(message_type) is expected
