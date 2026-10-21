"""Синхронизация логотипов эмитентов (каркас CLI).

TODO: копирование курируемых SVG из assets/logos в static/logos и upsert
tickers.logo_url; отсутствующие ассеты — WARNING, logo_url = NULL.
"""

import argparse
import logging

from app.core.logging import setup_logging

logger = logging.getLogger("sync_logos")


def build_parser() -> argparse.ArgumentParser:
    """Описывает CLI-контракт скрипта."""
    parser = argparse.ArgumentParser(description="Синхронизация логотипов эмитентов")
    parser.add_argument("--source", default="assets", choices=["assets"], help="Источник ассетов")
    parser.add_argument("--dry-run", action="store_true", help="Без записи в БД и файлов")
    parser.add_argument("--verbose", action="store_true", help="Уровень логирования DEBUG")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа; пока — заглушка с кодом возврата 1."""
    args = build_parser().parse_args(argv)
    setup_logging(logging.DEBUG if args.verbose else logging.INFO)

    logger.info("start source=%s dry_run=%s", args.source, args.dry_run)
    logger.error("синхронизация логотипов не реализована")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
