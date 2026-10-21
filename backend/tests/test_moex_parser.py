"""Тесты парсера MOEX ISS и нормализации тикеров на сохранённом ответе."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from scripts.ingestion.normalize import normalize_tickers
from scripts.ingestion.parsers.moex_tickers import (
    MoexFormatError,
    MoexSecurity,
    parse_securities_page,
)

FIXTURE = Path(__file__).parent / "fixtures" / "moex_securities.json"


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parse_keeps_only_requested_board(payload: dict) -> None:
    """Парсер оставляет бумаги TQBR и отбрасывает другие доски и пустые имена."""
    page = parse_securities_page(payload, board="TQBR")

    assert page.row_count == 5
    assert [fact.secid for fact in page.facts] == ["SBER", "GAZP", "MTLR"]


def test_parse_last_price_fallbacks(payload: dict) -> None:
    """LAST приоритетнее MARKETPRICE, затем PREVPRICE; иначе None."""
    facts = {fact.secid: fact for fact in parse_securities_page(payload).facts}

    assert facts["SBER"].last_price == Decimal("305.5")
    assert facts["GAZP"].last_price == Decimal("128.4")
    assert facts["MTLR"].last_price is None


def test_parse_security_fields(payload: dict) -> None:
    """Краткое и полное наименование, ISIN, доска и размер лота."""
    facts = {fact.secid: fact for fact in parse_securities_page(payload).facts}
    sber = facts["SBER"]

    assert sber.short_name == "Сбербанк"
    assert sber.full_name == "Сбербанк России ПАО ао"
    assert sber.isin == "RU0009029540"
    assert sber.board == "TQBR"
    assert sber.lot_size == 10


def test_parse_unknown_board(payload: dict) -> None:
    """Для доски SMAL возвращается только её бумага."""
    page = parse_securities_page(payload, board="SMAL")

    assert [fact.secid for fact in page.facts] == ["AFLT"]
    assert page.facts[0].last_price == Decimal("61.0")


def test_parse_broken_payload() -> None:
    """Отсутствие блока securities — доменная ошибка формата."""
    with pytest.raises(MoexFormatError):
        parse_securities_page({"marketdata": {}})


def test_normalize_tickers() -> None:
    """Тикеры приводятся к верхнему регистру и дедуплицируются."""
    fetched_at = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    facts = [
        MoexSecurity(
            "sber",
            "Сбербанк",
            "Сбербанк России ПАО ао",
            "RU0009029540",
            "TQBR",
            10,
            Decimal("305.5"),
        ),
        MoexSecurity("SBER", "Сбербанк (дубль)", None, None, "TQBR", 10, Decimal("306.0")),
        MoexSecurity("GAZP", "Газпром", None, None, "TQBR", 10, None),
    ]

    items = normalize_tickers(
        facts, source_url="https://iss.moex.com/iss/example.json", fetched_at=fetched_at
    )

    assert len(items) == 2
    by_ticker = {item.ticker: item for item in items}
    assert by_ticker["SBER"].short_name == "Сбербанк (дубль)"
    assert by_ticker["SBER"].last_price == Decimal("306.0")
    assert by_ticker["GAZP"].last_price is None
    assert by_ticker["GAZP"].fetched_at == fetched_at
