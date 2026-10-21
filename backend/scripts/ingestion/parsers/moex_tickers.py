"""Парсер JSON MOEX ISS: блоки securities и marketdata -> факты о тикерах."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

DEFAULT_BOARD = "TQBR"


class MoexFormatError(ValueError):
    """Неожиданная структура ответа MOEX ISS."""


@dataclass(frozen=True, slots=True)
class MoexSecurity:
    """Разобранный факт о бумаге с одной доски MOEX."""

    secid: str
    short_name: str
    full_name: str | None
    isin: str | None
    board: str
    lot_size: int | None
    last_price: Decimal | None


@dataclass(frozen=True, slots=True)
class ParsedSecuritiesPage:
    """Результат разбора одной страницы ответа."""

    facts: list[MoexSecurity]
    row_count: int
    total: int | None


def _index(columns: list[str]) -> dict[str, int]:
    return {name: position for position, name in enumerate(columns)}


def _value(row: list[Any], index: dict[str, int], name: str) -> Any:
    position = index.get(name)
    if position is None or position >= len(row):
        return None
    return row[position]


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _positive_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number <= 0:
        return None
    return number


def _positive_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _market_prices(block: Any) -> dict[tuple[str, str], Decimal]:
    """Цены из marketdata: LAST (последняя сделка), иначе MARKETPRICE."""
    if not isinstance(block, dict):
        return {}

    columns = block.get("columns")
    rows = block.get("data")
    if not isinstance(columns, list) or not isinstance(rows, list):
        return {}

    index = _index(columns)
    if "SECID" not in index or "BOARDID" not in index:
        return {}

    prices: dict[tuple[str, str], Decimal] = {}
    for row in rows:
        if not isinstance(row, list):
            continue
        secid = _clean_str(_value(row, index, "SECID"))
        board = _clean_str(_value(row, index, "BOARDID"))
        if secid is None or board is None:
            continue
        price = _positive_decimal(_value(row, index, "LAST"))
        if price is None:
            price = _positive_decimal(_value(row, index, "MARKETPRICE"))
        if price is not None:
            prices[(secid, board)] = price
    return prices


def _cursor_total(block: dict[str, Any]) -> int | None:
    cursor = block.get("cursor")
    if not isinstance(cursor, dict):
        return None
    columns = cursor.get("columns")
    rows = cursor.get("data")
    if not isinstance(columns, list) or not isinstance(rows, list) or not rows:
        return None
    mapping = dict(zip(columns, rows[0], strict=False))
    total = mapping.get("TOTAL")
    try:
        return int(total) if total is not None else None
    except (TypeError, ValueError):
        return None


def parse_securities_page(
    payload: Any, board: str = DEFAULT_BOARD
) -> ParsedSecuritiesPage:
    """Разбирает страницу ответа MOEX ISS и оставляет бумаги указанной доски.

    Парсер не ходит в сеть и не пишет в БД; неожиданная структура ответа
    поднимает MoexFormatError.
    """
    if not isinstance(payload, dict):
        raise MoexFormatError("response is not a JSON object")

    block = payload.get("securities")
    if not isinstance(block, dict):
        raise MoexFormatError("missing 'securities' block")

    columns = block.get("columns")
    rows = block.get("data")
    if not isinstance(columns, list) or not isinstance(rows, list):
        raise MoexFormatError("'securities' block has no columns/data")

    index = _index([str(name) for name in columns])
    required = {"SECID", "BOARDID", "SHORTNAME"}
    missing = required - index.keys()
    if missing:
        raise MoexFormatError(f"'securities' block lacks columns: {sorted(missing)}")

    prices = _market_prices(payload.get("marketdata"))
    facts: list[MoexSecurity] = []
    seen: set[str] = set()

    for row in rows:
        if not isinstance(row, list):
            continue
        secid = _clean_str(_value(row, index, "SECID"))
        board_id = _clean_str(_value(row, index, "BOARDID"))
        if secid is None:
            continue
        secid = secid.upper()
        if board_id != board or secid in seen:
            continue

        short_name = _clean_str(_value(row, index, "SHORTNAME"))
        if short_name is None:
            continue

        price = prices.get((secid, board_id))
        if price is None:
            price = _positive_decimal(_value(row, index, "PREVPRICE"))

        facts.append(
            MoexSecurity(
                secid=secid,
                short_name=short_name,
                full_name=_clean_str(_value(row, index, "SECNAME"))
                or _clean_str(_value(row, index, "LATNAME")),
                isin=_clean_str(_value(row, index, "ISIN")),
                board=board_id,
                lot_size=_positive_int(_value(row, index, "LOTSIZE")),
                last_price=price,
            )
        )
        seen.add(secid)

    return ParsedSecuritiesPage(
        facts=facts,
        row_count=len(rows),
        total=_cursor_total(block),
    )
