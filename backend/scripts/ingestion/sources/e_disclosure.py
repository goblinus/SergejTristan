"""Резервный адаптер Интерфакса: публичное зеркало disclosure.1prime.ru.

Сам e-disclosure.ru закрыт анти-бот-защитой и отдаёт автоматическим клиентам
connection reset, поэтому тот же поток сущфактов читается с публичного зеркала
Интерфакса. Формат сообщений стандартизован и совпадает с e-disclosure.ru.
"""

import logging
from datetime import date, timedelta

import httpx

from app.core.config import Settings
from scripts.ingestion.parsers.disclosure_events import (
    DisclosureFeedItem,
    is_candidate_message_type,
    parse_edisclosure_feed_page,
)
from scripts.ingestion.sources.common import fetch_text

NAME = "e-disclosure"
BASE_URL = "https://disclosure.1prime.ru"
FEED_URL = f"{BASE_URL}/news/"
MAX_PAGES = 20

logger = logging.getLogger(__name__)


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
    """Читает ленту зеркала Интерфакса за последние `lookback_days` дней."""
    cutoff = date.today() - timedelta(days=lookback_days)
    result: list[DisclosureFeedItem] = []

    for page_number in range(MAX_PAGES):
        url = FEED_URL if page_number == 0 else f"{FEED_URL}?p={page_number}"
        html = fetch_text(client, url, settings)
        page = parse_edisclosure_feed_page(html)
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

    logger.info(
        "stage=fetch source=%s candidates=%d", NAME, len(result)
    )
    return _dedupe(result)


def fetch_message(
    client: httpx.Client, item: DisclosureFeedItem, settings: Settings
) -> str:
    """Загружает HTML страницы сообщения."""
    return fetch_text(client, item.url, settings)
