"""Сбор собраний акционеров и дат отсечки (каркас CLI).

TODO: fetch (disclosure.ru / e-disclosure.ru) -> parse HTML -> normalize ->
upsert в shareholder_meetings и record_dates.
"""

import argparse
import logging

from app.core.logging import setup_logging

logger = logging.getLogger("fetch_meetings_disclosure")

SOURCES = ("disclosure", "e-disclosure")


def build_parser() -> argparse.ArgumentParser:
    """Описывает CLI-контракт скрипта."""
    parser = argparse.ArgumentParser(description="Сбор собраний и отсечек из disclosure")
    parser.add_argument(
        "--source", choices=SOURCES, default=None, help="Ограничить одним источником"
    )
    parser.add_argument("--dry-run", action="store_true", help="Без записи в БД")
    parser.add_argument("--verbose", action="store_true", help="Уровень логирования DEBUG")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа; пока — заглушка с кодом возврата 1."""
    args = build_parser().parse_args(argv)
    setup_logging(logging.DEBUG if args.verbose else logging.INFO)

    logger.info("start source=%s dry_run=%s", args.source or "all", args.dry_run)
    logger.error("сбор собраний не реализован")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
