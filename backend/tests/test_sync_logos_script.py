"""Тесты синхронизации логотипов: валидация SVG, копирование, logo_url."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import scripts.sync_logos as script
from app.models import Base, Ticker
from scripts.sync_logos import LogoSourceError, sync_logos

FETCHED_AT = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
VALID_SVG = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'


@pytest.fixture()
def factory() -> Iterator[sessionmaker]:
    """Фабрика сессий на временной SQLite в памяти."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield session_factory
    engine.dispose()


def _add_ticker(
    factory: sessionmaker,
    ticker: str,
    *,
    is_active: bool = True,
    logo_url: str | None = None,
) -> None:
    with factory() as session:
        session.add(
            Ticker(
                ticker=ticker,
                short_name=f"{ticker} ПАО",
                is_active=is_active,
                logo_url=logo_url,
                source_url="https://iss.moex.com/iss/example.json",
                fetched_at=FETCHED_AT,
            )
        )
        session.commit()


def _write_svg(directory: Path, name: str, content: str = VALID_SVG) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def _logo_urls(factory: sessionmaker) -> dict[str, str | None]:
    with factory() as session:
        return {
            row.ticker: row.logo_url
            for row in session.execute(select(Ticker)).scalars()
        }


def test_valid_asset_is_copied_and_logo_url_set(factory, tmp_path: Path) -> None:
    """Валидный SVG копируется в статику, logo_url проставляется."""
    _add_ticker(factory, "SBER")
    _add_ticker(factory, "GAZP", is_active=False)
    source = tmp_path / "assets"
    target = tmp_path / "static"
    _write_svg(source, "SBER.svg")

    with factory() as session:
        stats = sync_logos(session, source_dir=source, target_dir=target)
        session.commit()

    assert (target / "SBER.svg").read_text(encoding="utf-8") == VALID_SVG
    assert _logo_urls(factory) == {
        "GAZP": None,
        "SBER": "/static/logos/SBER.svg",
    }
    assert stats.assets_found == 1
    assert stats.assets_valid == 1
    assert stats.assets_broken == 0
    assert stats.tickers_with_logo == 1
    assert stats.files_copied == 1
    assert stats.tickers_updated == 1


@pytest.mark.parametrize(
    "content",
    ["not an xml document", "<html><body>logo</body></html>"],
    ids=["broken-xml", "non-svg-root"],
)
def test_invalid_asset_logs_warning_and_clears_logo(
    factory, tmp_path: Path, content: str
) -> None:
    """Битый или не-SVG файл пропускается, logo_url сбрасывается в NULL."""
    _add_ticker(factory, "BAD", logo_url="/static/logos/BAD.svg")
    _add_ticker(factory, "GOOD")
    source = tmp_path / "assets"
    target = tmp_path / "static"
    _write_svg(source, "bad.svg", content)
    _write_svg(source, "good.svg")

    with factory() as session:
        stats = sync_logos(session, source_dir=source, target_dir=target)
        session.commit()

    assert _logo_urls(factory) == {
        "BAD": None,
        "GOOD": "/static/logos/GOOD.svg",
    }
    assert stats.assets_found == 2
    assert stats.assets_valid == 1
    assert stats.assets_broken == 1
    assert stats.cleared == 1
    assert not (target / "BAD.svg").exists()


def test_ticker_without_asset_is_cleared(factory, tmp_path: Path) -> None:
    """Тикер без ассета получает logo_url = NULL."""
    _add_ticker(factory, "SBER", logo_url="/static/logos/SBER.svg")
    _add_ticker(factory, "GAZP")
    source = tmp_path / "assets"
    target = tmp_path / "static"
    _write_svg(source, "GAZP.svg")

    with factory() as session:
        stats = sync_logos(session, source_dir=source, target_dir=target)
        session.commit()

    assert _logo_urls(factory) == {
        "GAZP": "/static/logos/GAZP.svg",
        "SBER": None,
    }
    assert stats.cleared == 1


def test_dry_run_does_not_copy_or_write(factory, tmp_path: Path) -> None:
    """--dry-run проходит валидацию и подсчёт, но не трогает файлы и БД."""
    _add_ticker(factory, "SBER")
    source = tmp_path / "assets"
    target = tmp_path / "static"
    _write_svg(source, "SBER.svg")

    with factory() as session:
        stats = sync_logos(
            session, source_dir=source, target_dir=target, dry_run=True
        )
        session.commit()

    assert not target.exists()
    assert _logo_urls(factory) == {"SBER": None}
    assert stats.dry_run is True
    assert stats.files_copied == 0
    assert stats.tickers_with_logo == 1
    assert stats.tickers_updated == 1


@pytest.mark.parametrize("mode", ["missing", "empty"])
def test_fatal_source_returns_code_one_and_keeps_db(
    factory, tmp_path: Path, monkeypatch, mode: str
) -> None:
    """Отсутствующий или пустой каталог источника — код 1, БД не изменена."""
    _add_ticker(factory, "SBER", logo_url="/static/logos/SBER.svg")
    source = tmp_path / "assets"
    if mode == "empty":
        source.mkdir()
    target = tmp_path / "static"

    monkeypatch.setattr(script, "SessionLocal", factory)
    monkeypatch.setattr(script, "DEFAULT_SOURCE_DIR", source)
    monkeypatch.setattr(script, "DEFAULT_TARGET_DIR", target)

    code = script.main([])

    assert code == 1
    assert _logo_urls(factory) == {"SBER": "/static/logos/SBER.svg"}
    assert not target.exists()


def test_source_not_a_directory_raises(factory, tmp_path: Path) -> None:
    """Путь источника, не являющийся каталогом, — LogoSourceError."""
    _add_ticker(factory, "SBER")
    source = tmp_path / "assets.svg"
    _write_svg(tmp_path, "assets.svg")

    with factory() as session, pytest.raises(LogoSourceError):
        sync_logos(session, source_dir=source, target_dir=tmp_path / "static")

    assert _logo_urls(factory) == {"SBER": None}


def test_ticker_filename_is_case_insensitive(factory, tmp_path: Path) -> None:
    """`sber.svg` соответствует тикеру SBER, в статике имя в верхнем регистре."""
    _add_ticker(factory, "SBER")
    source = tmp_path / "assets"
    target = tmp_path / "static"
    _write_svg(source, "sber.svg")

    with factory() as session:
        sync_logos(session, source_dir=source, target_dir=target)
        session.commit()

    assert (target / "SBER.svg").is_file()
    # Windows не различает регистр в путях, поэтому сверяем фактическое имя файла.
    assert [path.name for path in target.iterdir()] == ["SBER.svg"]
    assert _logo_urls(factory) == {"SBER": "/static/logos/SBER.svg"}


def test_repeated_run_is_idempotent(factory, tmp_path: Path) -> None:
    """Повторный запуск не копирует и не обновляет уже синхронизированное."""
    _add_ticker(factory, "SBER")
    source = tmp_path / "assets"
    target = tmp_path / "static"
    _write_svg(source, "SBER.svg")

    with factory() as session:
        first = sync_logos(session, source_dir=source, target_dir=target)
        session.commit()
    assert first.files_copied == 1
    assert first.tickers_updated == 1

    with factory() as session:
        second = sync_logos(session, source_dir=source, target_dir=target)
        session.commit()

    assert second.files_copied == 0
    assert second.tickers_updated == 0
    assert second.cleared == 0
    assert _logo_urls(factory) == {"SBER": "/static/logos/SBER.svg"}
