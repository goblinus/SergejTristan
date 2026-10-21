"""Расчёт DSI по истории дивидендов MOEX (каркас CLI).

TODO: fetch истории дивидендов -> агрегация годовых DPS -> services.dividends.calc_dsi
-> upsert полей dsi и dsi_updated_at в tickers.
"""

import argparse
import logging

from app.core.logging import setup_logging

logger = logging.getLogger("fetch_dividend_history_moex")


def build_parser() -> argparse.ArgumentParser:
    """Описывает CLI-контракт скрипта."""
    parser = argparse.ArgumentParser(description="Расчёт DSI по истории дивидендов MOEX")
    parser.add_argument("--source", default="moex", choices=["moex"], help="Источник сбора")
    parser.add_argument("--dry-run", action="store_true", help="Без записи в БД")
    parser.add_argument("--verbose", action="store_true", help="Уровень логирования DEBUG")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа; пока — заглушка с кодом возврата 1."""
    args = build_parser().parse_args(argv)
    setup_logging(logging.DEBUG if args.verbose else logging.INFO)

    logger.info("start source=%s dry_run=%s", args.source, args.dry_run)
    logger.error("расчёт DSI не реализован")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
