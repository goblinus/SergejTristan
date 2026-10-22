"""Нормализация разобранных фактов в канонические DTO (вне API-схем)."""

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from scripts.ingestion.parsers.disclosure_events import DisclosureMessageFact
from scripts.ingestion.parsers.moex_tickers import MoexSecurity

logger = logging.getLogger(__name__)

MeetingType = Literal["annual", "extraordinary"]
DividendPeriod = Literal["year", "half_year", "quarter"]
RecordDateKind = Literal["dividend_payment", "meeting_participation"]

# Максимальный разрыв между собранием и отсечкой для эвристики связывания.
LINK_MAX_GAP_DAYS = 120


@dataclass(frozen=True, slots=True)
class TickerRef:
    """Минимальные данные тикера, нужные нормализации без ORM."""

    ticker: str
    short_name: str
    full_name: str | None
    isin: str | None


class NormalizedTicker(BaseModel):
    """Канонический тикер после нормализации."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticker: str = Field(min_length=1)
    short_name: str = Field(min_length=1)
    full_name: str | None = None
    isin: str | None = None
    board: str | None = None
    lot_size: int | None = None
    last_price: Decimal | None = Field(default=None, gt=0)
    source_url: str
    fetched_at: datetime

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        """SECID хранится в верхнем регистре без пробелов."""
        return value.strip().upper()


class NormalizedMeeting(BaseModel):
    """Каноническое собрание акционеров с вопросом о дивидендах."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticker: str
    meeting_date: date
    meeting_type: MeetingType
    dividend_question: bool = True
    dividend_period: DividendPeriod | None = None
    dividend_per_share: Decimal | None = Field(default=None, ge=0)
    description: str | None = None
    source_url: str
    fetched_at: datetime

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class NormalizedRecordDate(BaseModel):
    """Каноническая дата закрытия реестра."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticker: str
    record_date: date
    kind: RecordDateKind = "dividend_payment"
    meeting_id: int | None = None
    meeting_date: date | None = None
    meeting_type: MeetingType | None = None
    dividend_period: DividendPeriod | None = None
    source_url: str
    fetched_at: datetime

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


@dataclass
class NormalizedDisclosure:
    """Итог нормализации сообщений disclosure: собрания и отсечки."""

    meetings: list[NormalizedMeeting]
    record_dates: list[NormalizedRecordDate]
    skipped: int = 0


class NormalizedDividendMetrics(BaseModel):
    """DSI эмитента — материализованный снапшот (ADR-0005)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticker: str
    dsi: int | None = Field(default=None, ge=0, le=100)
    dsi_updated_at: datetime

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


def normalize_tickers(
    facts: Iterable[MoexSecurity], *, source_url: str, fetched_at: datetime
) -> list[NormalizedTicker]:
    """Приводит факты MOEX ISS к каноническим DTO и дедуплицирует по тикеру.

    Некорректная запись отбрасывается с WARNING, остальные обрабатываются.
    """
    result: dict[str, NormalizedTicker] = {}

    for fact in facts:
        try:
            item = NormalizedTicker(
                ticker=fact.secid,
                short_name=fact.short_name,
                full_name=fact.full_name,
                isin=fact.isin,
                board=fact.board,
                lot_size=fact.lot_size,
                last_price=fact.last_price,
                source_url=source_url,
                fetched_at=fetched_at,
            )
        except ValidationError as exc:
            logger.warning("skip ticker=%r: %s", fact.secid, exc.errors())
            continue
        result[item.ticker] = item

    return list(result.values())


_LEGAL_FORMS = (
    "публичное акционерное общество",
    "непубличное акционерное общество",
    "открытое акционерное общество",
    "закрытое акционерное общество",
    "акционерное общество",
    "общество с ограниченной ответственностью",
    "публичная компания",
    "мкпао",
    "пао",
    "оао",
    "зао",
    "ооо",
    "нао",
    "ппк",
    "ао",
)


def _fold(value: str) -> str:
    return value.casefold().replace("ё", "е")


def _normalize_name(value: str) -> str:
    """Нормализует наименование эмитента для сопоставления с тикером."""
    text = _fold(value)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()

    changed = True
    while changed:
        changed = False
        for form in _LEGAL_FORMS:
            if text.startswith(f"{form} "):
                text = text[len(form) + 1 :].strip()
                changed = True
            if text.endswith(f" {form}"):
                text = text[: -(len(form) + 1)].strip()
                changed = True

    text = re.sub(r"\b(?:имени|им)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _base_name(value: str) -> str:
    """Отбрасывает признак класса акций: -ао/-ап/-п, «обыкновенные»/«привилегированные»."""
    text = _normalize_name(value)
    text = re.sub(r"\b(?:ао|ап|об|оп|п)\s*$", "", text).strip()
    text = re.sub(r"\b(?:обыкновенн\w*|привилегированн\w*)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_preferred(ticker: TickerRef) -> bool:
    names = f"{_normalize_name(ticker.short_name)} {_normalize_name(ticker.full_name or '')}"
    return (
        re.search(r"(?:^|\s)(?:ап|п|привилегированн\w*)(?:\s|$)", names) is not None
    )


def _filter_by_class(candidates: list[TickerRef], text: str) -> list[TickerRef]:
    """Сужает совпадение по эмитенту, если сообщение говорит об одном классе акций."""
    folded = _fold(text)
    has_common = "обыкновен" in folded
    has_preferred = "привилегирован" in folded
    if has_preferred and not has_common:
        preferred = [ticker for ticker in candidates if _is_preferred(ticker)]
        return preferred or candidates
    if has_common and not has_preferred:
        ordinary = [ticker for ticker in candidates if not _is_preferred(ticker)]
        return ordinary or candidates
    return candidates


def _contains_tokens(haystack: str, needle: str) -> bool:
    return re.search(rf"(?:^|\s){re.escape(needle)}(?:$|\s)", haystack) is not None


def _expand_class_siblings(
    candidates: list[TickerRef], ticker_list: list[TickerRef]
) -> list[TickerRef]:
    """Добавляет тикеры других классов того же эмитента (обыкновенные/привилегированные)."""
    bases = {
        base
        for ticker in candidates
        for base in (_base_name(ticker.short_name), _base_name(ticker.full_name or ""))
        if len(base) >= 4
    }
    if not bases:
        return candidates

    result = list(candidates)
    for ticker in ticker_list:
        if ticker in result:
            continue
        ticker_bases = {_base_name(ticker.short_name), _base_name(ticker.full_name or "")}
        if bases & ticker_bases:
            result.append(ticker)
    return result


def match_tickers(fact: DisclosureMessageFact, tickers: Iterable[TickerRef]) -> list[TickerRef]:
    """Сопоставляет сообщение с активными тикерами по ISIN или наименованию эмитента."""
    ticker_list = list(tickers)
    if not ticker_list:
        return []

    if fact.isins:
        isin_set = {isin.upper() for isin in fact.isins}
        by_isin = [
            ticker
            for ticker in ticker_list
            if ticker.isin is not None and ticker.isin.upper() in isin_set
        ]
        # ISIN в сообщении — точный признак бумаги. Если ни один не совпал,
        # сообщение относится к другой бумаге (например, облигации) и не должно
        # сопоставляться с акцией только по названию эмитента.
        return _filter_by_class(by_isin, fact.text) if by_isin else []

    if not fact.issuer_name:
        return []
    issuer = _normalize_name(fact.issuer_name)
    if not issuer:
        return []

    exact_full = [
        ticker
        for ticker in ticker_list
        if ticker.full_name is not None and _normalize_name(ticker.full_name) == issuer
    ]
    if exact_full:
        return _filter_by_class(
            _expand_class_siblings(exact_full, ticker_list), fact.text
        )

    exact_short = [
        ticker for ticker in ticker_list if _normalize_name(ticker.short_name) == issuer
    ]
    if exact_short:
        return _filter_by_class(
            _expand_class_siblings(exact_short, ticker_list), fact.text
        )

    hits: list[TickerRef] = []
    for ticker in ticker_list:
        names = {_base_name(ticker.short_name), _base_name(ticker.full_name or "")}
        if any(len(name) >= 4 and _contains_tokens(issuer, name) for name in names):
            hits.append(ticker)

    if 0 < len(hits) <= 5:
        return _filter_by_class(hits, fact.text)
    return []


def _merge_meeting(
    current: NormalizedMeeting | None, item: NormalizedMeeting
) -> NormalizedMeeting:
    if current is None:
        return item

    description = current.description
    if item.description and (description is None or len(item.description) > len(description)):
        description = item.description

    has_new_terms = item.dividend_period is not None or item.dividend_per_share is not None
    return NormalizedMeeting(
        ticker=current.ticker,
        meeting_date=current.meeting_date,
        meeting_type=current.meeting_type,
        dividend_question=current.dividend_question or item.dividend_question,
        dividend_period=current.dividend_period or item.dividend_period,
        dividend_per_share=(
            current.dividend_per_share
            if current.dividend_per_share is not None
            else item.dividend_per_share
        ),
        description=description,
        source_url=item.source_url if has_new_terms else current.source_url,
        fetched_at=max(current.fetched_at, item.fetched_at),
    )


def _merge_record_date(
    current: NormalizedRecordDate | None, item: NormalizedRecordDate
) -> NormalizedRecordDate:
    if current is None:
        return item
    return NormalizedRecordDate(
        ticker=current.ticker,
        record_date=current.record_date,
        kind=current.kind,
        meeting_id=current.meeting_id or item.meeting_id,
        meeting_date=current.meeting_date or item.meeting_date,
        meeting_type=current.meeting_type or item.meeting_type,
        dividend_period=current.dividend_period or item.dividend_period,
        source_url=item.source_url,
        fetched_at=max(current.fetched_at, item.fetched_at),
    )


def _link_record_dates(
    meetings: list[NormalizedMeeting], record_dates: list[NormalizedRecordDate]
) -> list[NormalizedRecordDate]:
    """Связывает отсечки с собраниями по эмитенту и близости дат.

    Для dividend_payment собрание предшествует отсечке, для
    meeting_participation — наоборот. При неоднозначной близости связь не ставится.
    """
    by_ticker: dict[str, list[NormalizedMeeting]] = {}
    for meeting in meetings:
        by_ticker.setdefault(meeting.ticker, []).append(meeting)

    result: list[NormalizedRecordDate] = []
    for record_date in record_dates:
        if record_date.meeting_date is not None and record_date.meeting_type is not None:
            result.append(record_date)
            continue

        candidates: list[NormalizedMeeting] = []
        for meeting in by_ticker.get(record_date.ticker, []):
            gap = (meeting.meeting_date - record_date.record_date).days
            if record_date.kind == "dividend_payment":
                # Собрание предшествует выплате: meeting_date <= record_date.
                if -LINK_MAX_GAP_DAYS <= gap <= 0:
                    candidates.append(meeting)
            elif 0 <= gap <= LINK_MAX_GAP_DAYS:
                # Участие: отсечка предшествует собранию.
                candidates.append(meeting)

        if (
            record_date.kind == "dividend_payment"
            and record_date.dividend_period is not None
        ):
            same_period = [
                meeting
                for meeting in candidates
                if meeting.dividend_period == record_date.dividend_period
            ]
            if same_period:
                candidates = same_period

        linked = None
        if len(candidates) == 1:
            linked = candidates[0]
        elif len(candidates) > 1:
            candidates.sort(
                key=lambda meeting: abs(
                    (meeting.meeting_date - record_date.record_date).days
                )
            )
            first_gap = abs((candidates[0].meeting_date - record_date.record_date).days)
            second_gap = abs((candidates[1].meeting_date - record_date.record_date).days)
            if first_gap < second_gap:
                linked = candidates[0]

        if linked is not None:
            record_date = record_date.model_copy(
                update={
                    "meeting_date": linked.meeting_date,
                    "meeting_type": linked.meeting_type,
                }
            )
        result.append(record_date)

    return result


def normalize_disclosure_messages(
    facts: Iterable[DisclosureMessageFact],
    tickers: Iterable[TickerRef],
    *,
    fetched_at: datetime,
) -> NormalizedDisclosure:
    """Приводит разобранные сообщения disclosure к каноническим DTO.

    Сообщения об объявлении собрания и об итогах объединяются по бизнес-ключу
    собрания; непустые поля не затираются. Отсечки без явной связи с собранием
    связываются эвристикой по датам.
    """
    ticker_list = list(tickers)
    meetings: dict[tuple[str, date, str], NormalizedMeeting] = {}
    record_dates: dict[tuple[str, date, str], NormalizedRecordDate] = {}
    skipped = 0

    for fact in facts:
        matches = match_tickers(fact, ticker_list)
        if not matches:
            logger.debug("skip unmatched issuer=%r url=%s", fact.issuer_name, fact.url)
            skipped += 1
            continue

        for ticker in matches:
            try:
                if fact.message_kind in {"meeting", "results"}:
                    if not fact.dividend_question:
                        skipped += 1
                        continue
                    if fact.meeting_date is None or fact.meeting_type is None:
                        logger.warning(
                            "skip meeting ticker=%s url=%s: no date or type",
                            ticker.ticker,
                            fact.url,
                        )
                        skipped += 1
                        continue

                    meeting = NormalizedMeeting(
                        ticker=ticker.ticker,
                        meeting_date=fact.meeting_date,
                        meeting_type=fact.meeting_type,
                        dividend_question=True,
                        dividend_period=fact.dividend_period,
                        dividend_per_share=fact.dividend_per_share,
                        description=fact.description,
                        source_url=fact.url,
                        fetched_at=fetched_at,
                    )
                    key = (meeting.ticker, meeting.meeting_date, meeting.meeting_type)
                    meetings[key] = _merge_meeting(meetings.get(key), meeting)

                if (
                    fact.record_date is not None
                    and fact.record_date_kind
                    in {"dividend_payment", "meeting_participation"}
                ):
                    record_date = NormalizedRecordDate(
                        ticker=ticker.ticker,
                        record_date=fact.record_date,
                        kind=fact.record_date_kind,
                        meeting_date=(
                            fact.meeting_date
                            if fact.message_kind in {"meeting", "results"}
                            else None
                        ),
                        meeting_type=(
                            fact.meeting_type
                            if fact.message_kind in {"meeting", "results"}
                            else None
                        ),
                        dividend_period=fact.dividend_period,
                        source_url=fact.url,
                        fetched_at=fetched_at,
                    )
                    key = (record_date.ticker, record_date.record_date, record_date.kind)
                    record_dates[key] = _merge_record_date(
                        record_dates.get(key), record_date
                    )
            except ValidationError as exc:
                logger.warning("skip ticker=%s url=%s: %s", ticker.ticker, fact.url, exc.errors())
                skipped += 1

    linked_record_dates = _link_record_dates(
        list(meetings.values()), list(record_dates.values())
    )
    return NormalizedDisclosure(
        meetings=sorted(
            meetings.values(), key=lambda item: (item.ticker, item.meeting_date, item.meeting_type)
        ),
        record_dates=sorted(
            linked_record_dates,
            key=lambda item: (item.ticker, item.record_date, item.kind),
        ),
        skipped=skipped,
    )
