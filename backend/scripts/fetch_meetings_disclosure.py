"""Сбор собраний акционеров и дат отсечки из disclosure.

Пайплайн: fetch (лента + страницы сообщений) -> parse -> normalize -> upsert
в shareholder_meetings и record_dates.

Коды возврата:
    0 — сбор успешен (данные записаны либо dry-run без ошибок);
    1 — фатальный сбой: недоступны все источники или БД;
    2 — частичный сбой: часть сообщений не удалось загрузить/разобрать.
"""

import argparse
import logging
from datetime import UTC, datetime

import httpx

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.repositories import tickers as tickers_repo
from scripts.ingestion.loader import load_meetings, load_record_dates
from scripts.ingestion.normalize import (
    TickerRef,
    normalize_disclosure_messages,
)
from scripts.ingestion.parsers.disclosure_events import parse_message
from scripts.ingestion.sources import disclosure, e_disclosure
from scripts.ingestion.sources.common import SourceError

logger = logging.getLogger("fetch_meetings_disclosure")

SOURCES = ("disclosure", "e-disclosure")
SOURCE_MODULES = {
    "disclosure": disclosure,
    "e-disclosure": e_disclosure,
}


def build_parser() -> argparse.ArgumentParser:
    """Описывает CLI-контракт скрипта."""
    parser = argparse.ArgumentParser(description="Сбор собраний и отсечек из disclosure")
    parser.add_argument(
        "--source", choices=SOURCES, default=None, help="Ограничить одним источником"
    )
    parser.add_argument("--dry-run", action="store_true", help="Без записи в БД")
    parser.add_argument("--verbose", action="store_true", help="Уровень логирования DEBUG")
    return parser


def _load_active_tickers() -> list[TickerRef]:
    """Читает активные тикеры из БД для сопоставления с сообщениями."""
    with SessionLocal() as session:
        return [
            TickerRef(
                ticker=ticker.ticker,
                short_name=ticker.short_name,
                full_name=ticker.full_name,
                isin=ticker.isin,
            )
            for ticker in tickers_repo.list_active_tickers(session)
        ]


def _collect_facts(
    source_name: str, settings, lookback_days: int
) -> tuple[list, int]:
    """Загружает и разбирает сообщения одного источника."""
    module = SOURCE_MODULES[source_name]
    facts = []
    parse_errors = 0

    with httpx.Client(
        timeout=settings.http_timeout_seconds, follow_redirects=True
    ) as client:
        feed_items = module.fetch_feed(client, settings, lookback_days)
        logger.info(
            "stage=fetch source=%s candidates=%d", source_name, len(feed_items)
        )
        for item in feed_items:
            try:
                html = module.fetch_message(client, item, settings)
                fact = parse_message(html, item)
            except (SourceError, ValueError) as exc:
                logger.warning(
                    "stage=parse source=%s url=%s error=%s",
                    source_name,
                    item.url,
                    exc,
                )
                parse_errors += 1
                continue
            if fact is None:
                logger.warning(
                    "stage=parse source=%s url=%s error=unrecognized message",
                    source_name,
                    item.url,
                )
                parse_errors += 1
                continue
            facts.append(fact)

    return facts, parse_errors


def main(argv: list[str] | None = None) -> int:
    """Запускает пайплайн сбора собраний и дат отсечки."""
    args = build_parser().parse_args(argv)

    try:
        settings = get_settings()
    except Exception:
        setup_logging(logging.INFO)
        logger.exception("stage=config failed")
        return 1

    setup_logging(logging.DEBUG if args.verbose else settings.log_level)
    logger.info(
        "start source=%s dry_run=%s lookback_days=%d",
        args.source or "all",
        args.dry_run,
        settings.disclosure_lookback_days,
    )

    try:
        tickers = _load_active_tickers()
    except Exception:
        logger.exception("stage=load failed to read active tickers")
        return 1

    if not tickers:
        logger.info("stage=normalize skipped: no active tickers")
        return 0

    source_names = [args.source] if args.source else list(SOURCES)
    facts: list = []
    parse_errors = 0
    source_used: str | None = None
    source_errors = 0

    for source_name in source_names:
        try:
            source_facts, source_parse_errors = _collect_facts(
                source_name, settings, settings.disclosure_lookback_days
            )
        except SourceError as exc:
            logger.error("stage=fetch source=%s unavailable: %s", source_name, exc)
            source_errors += 1
            continue

        facts = source_facts
        parse_errors = source_parse_errors
        source_used = source_name
        break

    if source_used is None:
        logger.error("stage=fetch all sources unavailable (%d)", source_errors)
        return 1

    fetched_at = datetime.now(UTC)
    normalized = normalize_disclosure_messages(facts, tickers, fetched_at=fetched_at)
    logger.info(
        "stage=normalize source=%s fetched=%d meetings=%d record_dates=%d"
        " skipped=%d parse_errors=%d",
        source_used,
        len(facts),
        len(normalized.meetings),
        len(normalized.record_dates),
        normalized.skipped,
        parse_errors,
    )

    if args.dry_run:
        logger.info(
            "stage=dry-run meetings=%d record_dates=%d",
            len(normalized.meetings),
            len(normalized.record_dates),
        )
        return 2 if parse_errors else 0

    try:
        with SessionLocal() as session:
            meeting_stats = load_meetings(session, normalized.meetings)
            record_date_stats = load_record_dates(session, normalized.record_dates)
            session.commit()
    except Exception:
        logger.exception("stage=load failed")
        return 1

    logger.info(
        "stage=load meetings inserted=%d updated=%d skipped=%d",
        meeting_stats.inserted,
        meeting_stats.updated,
        meeting_stats.skipped,
    )
    logger.info(
        "stage=load record_dates inserted=%d updated=%d skipped=%d",
        record_date_stats.inserted,
        record_date_stats.updated,
        record_date_stats.skipped,
    )
    logger.info("done source=%s parse_errors=%d", source_used, parse_errors)
    return 2 if parse_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
