"""Точка входа FastAPI-приложения «Дивидендный календарь»."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import meetings, record_dates, tickers, watchlist
from app.core.config import get_settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "static"
API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Настройка логирования при старте; миграции запускаются отдельной командой."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("divcal backend started, database_url=%s", settings.database_url)
    yield
    logger.info("divcal backend stopped")


def create_app() -> FastAPI:
    """Создаёт приложение и подключает роутеры и статику."""
    app = FastAPI(
        title="Дивидендный календарь",
        description="API сервиса отслеживания дивидендных событий Московской биржи",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """Проверка живости сервиса."""
        return {"status": "ok"}

    app.include_router(tickers.router, prefix=API_PREFIX)
    app.include_router(meetings.router, prefix=API_PREFIX)
    app.include_router(record_dates.router, prefix=API_PREFIX)
    app.include_router(watchlist.router, prefix=API_PREFIX)

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app


app = create_app()
