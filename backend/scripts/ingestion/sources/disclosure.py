"""Адаптер disclosure.ru (АК&М): лента сообщений эмитентов и страницы сущфактов."""

import logging
from datetime import date, timedelta

import httpx

from app.core.config import Settings
from scripts.ingestion.parsers.disclosure_events import (
    DisclosureFeedItem,
    is_candidate_message_type,
    parse_disclosure_feed_page,
)
from scripts.ingestion.sources.common import fetch_text

NAME = "disclosure"
BASE_URL = "https://www.disclosure.ru"
FEED_URL = f"{BASE_URL}/rus/corpnews/index.shtml"
MAX_PAGES = 200

logger = logging.getLogger(__name__)


def _feed_form(cursor: str | None) -> dict[str, str]:
    """Данные POST-формы ленты; `ts` — курсор следующей страницы."""
    return {
        "emname": "",
        "inn": "",
        "ogrn": "",
        "set_filter": "Применить",
        "ts": cursor or "",
    }


def _dedupe(items: list[DisclosureFeedItem]) -> list[DisclosureFeedItem]:
    seen: set[str] = set()
    result: list[DisclosureFeedItem] = []
    for item in items:
        if item.url in seen:
            continue
        seen.add(item.url)
        result.append(item)
    return result


def fetch_feed(
    client: httpx.Client, settings: Settings, lookback_days: int = 3
) -> list[DisclosureFeedItem]:
    """Читает ленту disclosure.ru за последние `lookback_days` дней.

    Возвращает только сообщения типов, относящихся к собраниям и датам отсечки.
    Пагинация источника — POST-форма с курсором `ts` (YYYYMMDDHHMMSS).
    """
    cutoff = date.today() - timedelta(days=lookback_days)
    html = fetch_text(client, FEED_URL, settings)
    page = parse_disclosure_feed_page(html)

    result: list[DisclosureFeedItem] = []
    seen_cursors: set[str] = set()
    pages = 0

    while True:
        pages += 1
        if not page.items:
            break

        for item in page.items:
            if item.published_at is not None and item.published_at.date() < cutoff:
                continue
            if is_candidate_message_type(item.message_type):
                result.append(item)

        oldest = min(
            (item.published_at for item in page.items if item.published_at is not None),
            default=None,
        )
        if oldest is not None and oldest.date() < cutoff:
            break

        cursor = page.next_cursor
        if cursor is None or cursor in seen_cursors:
            break
        seen_cursors.add(cursor)

        if pages >= MAX_PAGES:
            logger.warning("страница ленты limit=%d reached", MAX_PAGES)
            break

        html = fetch_text(
            client, FEED_URL, settings, method="POST", data=_feed_form(cursor)
        )
        page = parse_disclosure_feed_page(html)

    logger.info("stage=fetch source=%s pages=%d candidates=%d", NAME, pages, len(result))
    return _dedupe(result)


def fetch_message(
    client: httpx.Client, item: DisclosureFeedItem, settings: Settings
) -> str:
    """Загружает HTML страницы сообщения."""
    return fetch_text(client, item.url, settings)
