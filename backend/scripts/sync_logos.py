"""Синхронизация логотипов эмитентов: assets/logos -> static/logos -> tickers.logo_url.

Курируемые SVG из `assets/logos/{TICKER}.svg` валидируются как XML с корневым
элементом `<svg>`, копируются в статику API (`static/logos/{TICKER}.svg`) и
проставляются в `tickers.logo_url` для всех тикеров (включая неактивные).
Тикер без валидного ассета получает `logo_url = NULL` (UI показывает монограмму).

Коды возврата:
    0 — синхронизация завершена (в том числе при частичных WARNING);
    1 — фатальный сбой: каталог источника отсутствует/пуст, ошибка записи
        статики или БД. В этом случае БД и файлы не изменяются.
"""

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.repositories import tickers as tickers_repo

logger = logging.getLogger("sync_logos")

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = BACKEND_DIR / "assets" / "logos"
DEFAULT_TARGET_DIR = BACKEND_DIR / "static" / "logos"
LOGO_URL_TEMPLATE = "/static/logos/{ticker}.svg"
SVG_SUFFIX = ".svg"


class LogoSourceError(RuntimeError):
    """Источник ассетов отсутствует или не содержит ни одного SVG."""


@dataclass(frozen=True, slots=True)
class SyncStats:
    """Итог синхронизации логотипов."""

    assets_found: int = 0
    assets_valid: int = 0
    assets_broken: int = 0
    tickers_with_logo: int = 0
    cleared: int = 0
    files_copied: int = 0
    tickers_updated: int = 0
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class _Asset:
    """Валидный SVG-ассет: тикер, исходный файл и его содержимое."""

    ticker: str
    path: Path
    data: bytes


def build_parser() -> argparse.ArgumentParser:
    """Описывает CLI-контракт скрипта."""
    parser = argparse.ArgumentParser(description="Синхронизация логотипов эмитентов")
    parser.add_argument("--source", default="assets", choices=["assets"], help="Источник ассетов")
    parser.add_argument("--dry-run", action="store_true", help="Без записи в БД и файлов")
    parser.add_argument("--verbose", action="store_true", help="Уровень логирования DEBUG")
    return parser


def _is_svg_document(data: bytes) -> bool:
    """Проверяет, что данные — XML с корневым элементом `svg` (с namespace или без)."""
    root = ElementTree.fromstring(data)
    local_name = root.tag.rsplit("}", 1)[-1]
    return local_name == "svg"


def _collect_assets(source_dir: Path) -> tuple[dict[str, _Asset], int, int]:
    """Собирает и валидирует SVG источника.

    Возвращает (ассеты по тикерам, найдено файлов, битых файлов). Битый или
    не-SVG файл логируется WARNING и не попадает в ассеты.
    """
    if not source_dir.is_dir():
        raise LogoSourceError(f"каталог источника не найден: {source_dir}")

    paths = sorted(
        (
            path
            for path in source_dir.iterdir()
            if path.is_file() and path.suffix.lower() == SVG_SUFFIX
        ),
        key=lambda path: path.name,
    )
    if not paths:
        raise LogoSourceError(f"в каталоге источника нет SVG-файлов: {source_dir}")

    assets: dict[str, _Asset] = {}
    valid = 0
    broken = 0

    for path in paths:
        ticker = path.stem.upper()
        try:
            data = path.read_bytes()
            if not _is_svg_document(data):
                raise ValueError("корневой элемент не <svg>")
        except (OSError, ElementTree.ParseError, ValueError) as exc:
            logger.warning(
                "stage=validate file=%s ticker=%s error=%s", path.name, ticker, exc
            )
            broken += 1
            continue

        valid += 1
        if ticker in assets:
            logger.warning(
                "stage=validate ticker=%s duplicate=%s kept=%s",
                ticker,
                path.name,
                assets[ticker].path.name,
            )
            continue
        assets[ticker] = _Asset(ticker=ticker, path=path, data=data)

    return assets, len(paths), broken


def _copy_asset(asset: _Asset, target_dir: Path) -> bool:
    """Копирует ассет в статику, если файл отсутствует или содержимое изменилось.

    Возвращает True, если файл был записан.
    """
    target = target_dir / f"{asset.ticker}{SVG_SUFFIX}"
    if target.is_file() and target.read_bytes() == asset.data:
        return False

    target_dir.mkdir(parents=True, exist_ok=True)
    target.write_bytes(asset.data)
    return True


def sync_logos(
    session: Session,
    *,
    source_dir: Path,
    target_dir: Path,
    dry_run: bool = False,
) -> SyncStats:
    """Синхронизирует логотипы из `source_dir` в `target_dir` и `tickers.logo_url`.

    Чтение источника, валидация и подсчёт выполняются всегда; при `dry_run`
    файлы не копируются и БД не изменяется. Транзакцию фиксирует вызывающая
    сторона. `LogoSourceError` — фатальная ошибка источника (БД не тронута).
    """
    assets, found, broken = _collect_assets(source_dir)
    valid = found - broken
    logger.info(
        "stage=scan source=%s found=%d valid=%d broken=%d",
        source_dir,
        found,
        valid,
        broken,
    )

    db_tickers = tickers_repo.list_all_tickers(session)
    mapping: dict[str, str | None] = {}
    for row in db_tickers:
        asset = assets.get(row.ticker.upper())
        mapping[row.ticker] = (
            LOGO_URL_TEMPLATE.format(ticker=asset.ticker) if asset is not None else None
        )

    changed = [row for row in db_tickers if row.logo_url != mapping[row.ticker]]
    cleared = sum(1 for row in changed if mapping[row.ticker] is None)
    tickers_with_logo = sum(1 for value in mapping.values() if value is not None)

    files_copied = 0
    if dry_run:
        tickers_updated = len(changed)
        logger.info(
            "stage=dry-run assets=%d tickers=%d would_copy=%d would_update=%d",
            len(assets),
            len(db_tickers),
            len(assets),
            tickers_updated,
        )
    else:
        for ticker in sorted(assets):
            if _copy_asset(assets[ticker], target_dir):
                files_copied += 1
        tickers_updated = tickers_repo.update_logo_urls(session, mapping)

    return SyncStats(
        assets_found=found,
        assets_valid=valid,
        assets_broken=broken,
        tickers_with_logo=tickers_with_logo,
        cleared=cleared,
        files_copied=files_copied,
        tickers_updated=tickers_updated,
        dry_run=dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    """Запускает синхронизацию логотипов из каталога `assets/logos`."""
    args = build_parser().parse_args(argv)
    setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    logger.info("start source=%s dry_run=%s", args.source, args.dry_run)

    try:
        with SessionLocal() as session:
            stats = sync_logos(
                session,
                source_dir=DEFAULT_SOURCE_DIR,
                target_dir=DEFAULT_TARGET_DIR,
                dry_run=args.dry_run,
            )
            if not args.dry_run:
                session.commit()
    except LogoSourceError as exc:
        logger.error("stage=source failed: %s", exc)
        return 1
    except Exception:
        logger.exception("stage=sync failed")
        return 1

    logger.info(
        "done assets_found=%d valid=%d broken=%d tickers_with_logo=%d"
        " cleared=%d updated=%d files_copied=%d dry_run=%s",
        stats.assets_found,
        stats.assets_valid,
        stats.assets_broken,
        stats.tickers_with_logo,
        stats.cleared,
        stats.tickers_updated,
        stats.files_copied,
        stats.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
