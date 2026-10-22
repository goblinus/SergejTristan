"""Идемпотентная загрузка нормализованных DTO в БД через репозитории."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.shareholder_meeting import ShareholderMeeting
from app.repositories import meetings as meetings_repo
from app.repositories import record_dates as record_dates_repo
from app.repositories import tickers as tickers_repo
from app.repositories.meetings import MeetingUpsert
from app.repositories.record_dates import RecordDateUpsert
from app.repositories.tickers import TickerUpsert
from scripts.ingestion.normalize import (
    LINK_MAX_GAP_DAYS,
    NormalizedDividendMetrics,
    NormalizedMeeting,
    NormalizedRecordDate,
    NormalizedTicker,
)


@dataclass
class LoadStats:
    """Итог загрузки одной сущности."""

    inserted: int = 0
    updated: int = 0
    skipped: int = 0


def load_tickers(session: Session, items: list[NormalizedTicker]) -> LoadStats:
    """Upsert тикеров по бизнес-ключу `ticker`."""
    upserts = [
        TickerUpsert(
            ticker=item.ticker,
            short_name=item.short_name,
            full_name=item.full_name,
            isin=item.isin,
            board=item.board,
            lot_size=item.lot_size,
            last_price=item.last_price,
            price_updated_at=item.fetched_at if item.last_price is not None else None,
            source_url=item.source_url,
            fetched_at=item.fetched_at,
        )
        for item in items
    ]
    inserted, updated = tickers_repo.upsert_tickers(session, upserts)
    return LoadStats(inserted=inserted, updated=updated)


def deactivate_missing_tickers(
    session: Session,
    active_tickers: set[str],
    *,
    board: str,
    source_url: str,
) -> int:
    """Деактивирует тикеры доски, не попавшие в текущий успешный сбор."""
    return tickers_repo.deactivate_missing(
        session, active_tickers, board=board, source_url=source_url
    )


def _meeting_key(item: NormalizedMeeting) -> tuple[str, date, str]:
    return item.ticker, item.meeting_date, item.meeting_type


def _merge_meetings(
    items: list[NormalizedMeeting],
) -> dict[tuple[str, date, str], NormalizedMeeting]:
    """Схлопывает повторы по бизнес-ключу, не затирая непустые поля."""
    merged: dict[tuple[str, date, str], NormalizedMeeting] = {}
    for item in items:
        key = _meeting_key(item)
        current = merged.get(key)
        if current is None:
            merged[key] = item
            continue

        description = current.description
        if item.description and (
            description is None or len(item.description) > len(description)
        ):
            description = item.description

        has_new_terms = (
            item.dividend_period is not None or item.dividend_per_share is not None
        )
        merged[key] = NormalizedMeeting(
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
    return merged


def load_meetings(session: Session, items: list[NormalizedMeeting]) -> LoadStats:
    """Upsert собраний по (ticker_id, meeting_date, meeting_type)."""
    if not items:
        return LoadStats()

    ticker_ids = {
        ticker.ticker: ticker.id for ticker in tickers_repo.list_active_tickers(session)
    }
    upserts: list[MeetingUpsert] = []
    skipped = 0

    for (ticker, _, _), item in _merge_meetings(items).items():
        ticker_id = ticker_ids.get(ticker)
        if ticker_id is None:
            skipped += 1
            continue
        upserts.append(
            MeetingUpsert(
                ticker_id=ticker_id,
                meeting_date=item.meeting_date,
                meeting_type=item.meeting_type,
                dividend_question=item.dividend_question,
                dividend_period=item.dividend_period,
                dividend_per_share=item.dividend_per_share,
                description=item.description,
                source_url=item.source_url,
                fetched_at=item.fetched_at,
            )
        )

    inserted, updated = meetings_repo.upsert_meetings(session, upserts)
    return LoadStats(inserted=inserted, updated=updated, skipped=skipped)


def _record_date_key(item: NormalizedRecordDate) -> tuple[str, date, str]:
    return item.ticker, item.record_date, item.kind


def _merge_record_dates(
    items: list[NormalizedRecordDate],
) -> dict[tuple[str, date, str], NormalizedRecordDate]:
    merged: dict[tuple[str, date, str], NormalizedRecordDate] = {}
    for item in items:
        key = _record_date_key(item)
        current = merged.get(key)
        if current is None:
            merged[key] = item
            continue
        merged[key] = NormalizedRecordDate(
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
    return merged


def load_record_dates(session: Session, items: list[NormalizedRecordDate]) -> LoadStats:
    """Upsert дат отсечки по (ticker_id, record_date, kind).

    Связь с собранием разрешается по бизнес-ключу (ticker, meeting_date,
    meeting_type), вычисленному нормализатором.
    """
    if not items:
        return LoadStats()

    ticker_ids = {
        ticker.ticker: ticker.id for ticker in tickers_repo.list_active_tickers(session)
    }
    meeting_ids = {
        (row.ticker_id, row.meeting_date, row.meeting_type): (
            row.id,
            row.dividend_period,
        )
        for row in session.execute(
            select(ShareholderMeeting).where(
                ShareholderMeeting.ticker_id.in_(set(ticker_ids.values()))
            )
        ).scalars()
    }

    upserts: list[RecordDateUpsert] = []
    skipped = 0

    for (ticker, _, _), item in _merge_record_dates(items).items():
        ticker_id = ticker_ids.get(ticker)
        if ticker_id is None:
            skipped += 1
            continue

        meeting_id = item.meeting_id
        if meeting_id is None:
            meeting_id = _resolve_meeting_id(
                meeting_ids,
                ticker_id=ticker_id,
                record_date=item.record_date,
                kind=item.kind,
                meeting_date=item.meeting_date,
                meeting_type=item.meeting_type,
                dividend_period=item.dividend_period,
            )

        upserts.append(
            RecordDateUpsert(
                ticker_id=ticker_id,
                meeting_id=meeting_id,
                record_date=item.record_date,
                kind=item.kind,
                source_url=item.source_url,
                fetched_at=item.fetched_at,
            )
        )

    inserted, updated = record_dates_repo.upsert_record_dates(session, upserts)
    return LoadStats(inserted=inserted, updated=updated, skipped=skipped)


def _resolve_meeting_id(
    meeting_ids: dict[tuple[int, date, str], tuple[int, str | None]],
    *,
    ticker_id: int,
    record_date: date,
    kind: str,
    meeting_date: date | None,
    meeting_type: str | None,
    dividend_period: str | None,
) -> int | None:
    """Находит собрание для отсечки, включая собранные в предыдущих прогонах.

    Сначала используется точный бизнес-ключ нормализатора, затем — эвристика
    близости дат с приоритетом совпадения периода выплаты.
    """
    if meeting_date is not None and meeting_type is not None:
        exact = meeting_ids.get((ticker_id, meeting_date, meeting_type))
        if exact is not None:
            return exact[0]

    candidates: list[tuple[int, int, int]] = []
    for (meeting_ticker_id, candidate_date, _), (meeting_id, period) in meeting_ids.items():
        if meeting_ticker_id != ticker_id:
            continue
        gap = (candidate_date - record_date).days
        if kind == "dividend_payment" and -LINK_MAX_GAP_DAYS <= gap <= 0:
            period_mismatch = 1 if dividend_period and period != dividend_period else 0
            candidates.append((period_mismatch, abs(gap), meeting_id))
        elif kind == "meeting_participation" and 0 <= gap <= LINK_MAX_GAP_DAYS:
            candidates.append((0, abs(gap), meeting_id))

    if not candidates:
        return None

    if dividend_period:
        same_period = [candidate for candidate in candidates if candidate[0] == 0]
        if same_period:
            candidates = same_period

    candidates.sort(key=lambda candidate: candidate[1])
    if len(candidates) == 1:
        return candidates[0][2]
    if candidates[0][1] < candidates[1][1]:
        return candidates[0][2]
    return None


def load_dividend_metrics(
    session: Session, items: list[NormalizedDividendMetrics]
) -> LoadStats:
    """Обновление снапшота DSI у тикеров (`dsi`, `dsi_updated_at`).

    TODO: реализовать после появления update-функции в app/repositories/tickers.py.
    """
    raise NotImplementedError
