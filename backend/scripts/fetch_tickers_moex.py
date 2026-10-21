"""Сбор списка тикеров MOEX ISS: fetch -> parse -> normalize -> upsert.

Коды возврата:
    0 — сбор успешен;
    1 — источник недоступен (данные не записаны, деактивация не выполняется);
    2 — неожиданный формат ответа источника.
"""

import argparse
import logging
from datetime import UTC, datetime

import httpx

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import setup_logging
from scripts.ingestion.loader import deactivate_missing_tickers, load_tickers
from scripts.ingestion.normalize import normalize_tickers
from scripts.ingestion.parsers.moex_tickers import DEFAULT_BOARD
from scripts.ingestion.sources.moex_iss import (
    BASE_URL,
    MoexFormatSourceError,
    MoexSourceError,
    fetch_securities,
)

logger = logging.getLogger("fetch_tickers_moex")


def build_parser() -> argparse.ArgumentParser:
    """Описывает CLI-контракт скрипта."""
    parser = argparse.ArgumentParser(description="Сбор тикеров с MOEX ISS")
    parser.add_argument("--source", default="moex", choices=["moex"], help="Источник сбора")
    parser.add_argument("--dry-run", action="store_true", help="Без записи в БД")
    parser.add_argument("--verbose", action="store_true", help="Уровень логирования DEBUG")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Запускает пайплайн сбора тикеров."""
    args = build_parser().parse_args(argv)
    setup_logging(logging.DEBUG if args.verbose else logging.INFO)

    settings = get_settings()
    logger.info("start source=%s dry_run=%s", args.source, args.dry_run)

    try:
        with httpx.Client(timeout=settings.http_timeout_seconds) as client:
            facts = fetch_securities(client, settings, board=DEFAULT_BOARD)
    except MoexFormatSourceError as exc:
        logger.error("stage=fetch unexpected format: %s", exc)
        return 2
    except MoexSourceError as exc:
        logger.error("stage=fetch source unavailable: %s", exc)
        return 1

    fetched_at = datetime.now(UTC)
    normalized = normalize_tickers(facts, source_url=BASE_URL, fetched_at=fetched_at)
    logger.info("stage=normalize fetched=%d normalized=%d", len(facts), len(normalized))

    if not normalized:
        logger.info("stage=load skipped: no tickers received, deactivation not performed")
        return 0

    if args.dry_run:
        logger.info("stage=dry-run ready=%d board=%s", len(normalized), DEFAULT_BOARD)
        return 0

    try:
        with SessionLocal() as session:
            stats = load_tickers(session, normalized)
            deactivated = deactivate_missing_tickers(
                session,
                {item.ticker for item in normalized},
                board=DEFAULT_BOARD,
                source_url=BASE_URL,
            )
            session.commit()
    except Exception:
        logger.exception("stage=load failed")
        return 1

    logger.info(
        "stage=load inserted=%d updated=%d deactivated=%d",
        stats.inserted,
        stats.updated,
        deactivated,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
