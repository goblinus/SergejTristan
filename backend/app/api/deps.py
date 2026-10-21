"""Общие зависимости роутеров: сессия БД и параметры пагинации."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_session

SessionDep = Annotated[Session, Depends(get_session)]


@dataclass(frozen=True)
class PageParams:
    """Параметры пагинации списков."""

    page: int
    page_size: int


def get_page_params(
    page: int = Query(1, ge=1, description="Номер страницы, начиная с 1"),
    page_size: int = Query(50, ge=1, le=100, description="Размер страницы, 1..100"),
) -> PageParams:
    """Валидирует page/page_size и упаковывает их вместе."""
    return PageParams(page=page, page_size=page_size)


PageDep = Annotated[PageParams, Depends(get_page_params)]
