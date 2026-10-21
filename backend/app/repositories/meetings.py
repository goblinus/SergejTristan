"""Репозиторий собраний акционеров."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.shareholder_meeting import ShareholderMeeting
from app.models.ticker import Ticker


@dataclass(frozen=True, slots=True)
class MeetingUpsert:
    """Данные собрания для идемпотентного upsert из скриптов сбора."""

    ticker_id: int
    meeting_date: date
    meeting_type: str
    dividend_question: bool
    dividend_period: str | None
    dividend_per_share: Decimal | None
    description: str | None
    source_url: str
    fetched_at: datetime


def _meetings_query(date_from: date, date_to: date, ticker: str | None) -> Select:
    """Базовый запрос календаря: собрания с вопросом о дивидендах в интервале."""
    stmt = (
        select(ShareholderMeeting)
        .join(ShareholderMeeting.ticker)
        .where(
            ShareholderMeeting.dividend_question.is_(True),
            ShareholderMeeting.meeting_date >= date_from,
            ShareholderMeeting.meeting_date <= date_to,
        )
    )
    if ticker is not None:
        stmt = stmt.where(Ticker.ticker == ticker)
    return stmt


def list_meetings(
    session: Session,
    date_from: date,
    date_to: date,
    ticker: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ShareholderMeeting], int]:
    """Собрания с dividend_question = true в [date_from, date_to], meeting_date ASC.

    Связанные отсечки и тикер загружаются eager-загрузкой, чтобы сервисный слой
    собирал DTO без N+1.
    """
    stmt = _meetings_query(date_from, date_to, ticker)
    total = session.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()

    rows = list(
        session.execute(
            stmt.options(
                selectinload(ShareholderMeeting.ticker),
                selectinload(ShareholderMeeting.record_dates),
            )
            .order_by(ShareholderMeeting.meeting_date.asc(), ShareholderMeeting.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars()
    )
    return rows, total


def get_meeting(session: Session, meeting_id: int) -> ShareholderMeeting | None:
    """Собрание по внутреннему id с тикером и связанными отсечками."""
    return session.execute(
        select(ShareholderMeeting)
        .where(ShareholderMeeting.id == meeting_id)
        .options(
            selectinload(ShareholderMeeting.ticker),
            selectinload(ShareholderMeeting.record_dates),
        )
    ).scalar_one_or_none()


def upsert_meetings(
    session: Session, items: Iterable[MeetingUpsert]
) -> tuple[int, int]:
    """Идемпотентный upsert по бизнес-ключу (ticker_id, meeting_date, meeting_type).

    Возвращает (вставлено, обновлено). При обновлении непустые поля данных
    не затираются пустыми значениями: объявление собрания и сообщение об итогах
    могут приходить разными записями источника.
    """
    by_key = {(item.ticker_id, item.meeting_date, item.meeting_type): item for item in items}
    if not by_key:
        return 0, 0

    existing = {
        (row.ticker_id, row.meeting_date, row.meeting_type): row
        for row in session.execute(
            select(ShareholderMeeting).where(
                ShareholderMeeting.ticker_id.in_({key[0] for key in by_key})
            )
        ).scalars()
    }

    inserted = 0
    updated = 0

    for key, item in by_key.items():
        row = existing.get(key)
        if row is None:
            session.add(
                ShareholderMeeting(
                    ticker_id=item.ticker_id,
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
            inserted += 1
        else:
            row.dividend_question = item.dividend_question
            if item.dividend_period is not None:
                row.dividend_period = item.dividend_period
            if item.dividend_per_share is not None:
                row.dividend_per_share = item.dividend_per_share
            if item.description is not None and (
                row.description is None or len(item.description) >= len(row.description)
            ):
                row.description = item.description
            row.source_url = item.source_url
            row.fetched_at = item.fetched_at
            updated += 1

    session.flush()
    return inserted, updated
