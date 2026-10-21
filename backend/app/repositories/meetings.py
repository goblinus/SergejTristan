"""Репозиторий собраний акционеров."""

from datetime import date

from sqlalchemy.orm import Session

from app.models.shareholder_meeting import ShareholderMeeting


def list_meetings(
    session: Session,
    date_from: date,
    date_to: date,
    ticker: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ShareholderMeeting], int]:
    """Собрания с dividend_question = true в [date_from, date_to], meeting_date ASC.

    TODO: реализовать join с tickers (для DTO), фильтр по тикеру, offset/limit и count.
    Пока — пустой результат для каркаса API.
    """
    return [], 0


def get_meeting(session: Session, meeting_id: int) -> ShareholderMeeting | None:
    """Собрание по внутреннему id.

    TODO: реализовать выборку (join с tickers и связанной отсечкой).
    """
    return None
