"""Общие Pydantic-схемы: конверт пагинации, ошибка, UTC-метки времени."""

from datetime import UTC, datetime
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field, PlainSerializer

T = TypeVar("T")


def _serialize_utc(value: datetime) -> str:
    """Форматирует метку времени как ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ).

    SQLite не сохраняет tzinfo, поэтому наивное значение трактуется как UTC.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


UtcDatetime = Annotated[
    datetime, PlainSerializer(_serialize_utc, return_type=str, when_used="json")
]


class Page(BaseModel, Generic[T]):
    """Конверт пагинации списков API."""

    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class ErrorResponse(BaseModel):
    """Стандартный формат ошибки FastAPI."""

    detail: str
