"""Общие функции HTTP-адаптеров источников: повторы и декодирование HTML."""

import logging
import time

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class SourceError(RuntimeError):
    """Источник недоступен или вернул недопустимый ответ."""


class SourceFormatError(SourceError):
    """Ответ источника не соответствует ожидаемой структуре."""


def _decode(response: httpx.Response) -> str:
    """Декодирует HTML с учётом windows-1251 (disclosure.ru, зеркало ПРАЙМ)."""
    encoding = response.encoding
    if encoding and encoding.lower() not in {"iso-8859-1", "ascii"}:
        return response.content.decode(encoding, errors="replace")

    for candidate in ("utf-8", "cp1251"):
        try:
            return response.content.decode(candidate)
        except UnicodeDecodeError:
            continue
    return response.content.decode("cp1251", errors="replace")


def fetch_text(
    client: httpx.Client,
    url: str,
    settings: Settings,
    *,
    method: str = "GET",
    data: dict[str, str] | None = None,
) -> str:
    """Загружает текст с повторами на сетевых ошибках, 5xx и 429.

    HTTP 4xx (кроме 429) не повторяются. Задержка между попытками —
    1, 2, 4, ... секунды.
    """
    attempt = 0

    while True:
        try:
            response = client.request(method, url, data=data)
            response.raise_for_status()
            return _decode(response)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if 400 <= status < 500 and status != 429:
                raise SourceError(f"HTTP {status} for {url}") from exc
            if attempt >= settings.http_retries:
                raise SourceError(
                    f"HTTP {status} for {url} after {attempt + 1} attempts"
                ) from exc
            delay = 2**attempt
            logger.warning(
                "retry url=%s attempt=%d status=%d delay=%ds",
                url,
                attempt + 1,
                status,
                delay,
            )
            attempt += 1
            time.sleep(delay)
        except httpx.RequestError as exc:
            if attempt >= settings.http_retries:
                raise SourceError(
                    f"request failed for {url} after {attempt + 1} attempts: {exc}"
                ) from exc
            delay = 2**attempt
            logger.warning(
                "retry url=%s attempt=%d error=%s delay=%ds",
                url,
                attempt + 1,
                type(exc).__name__,
                delay,
            )
            attempt += 1
            time.sleep(delay)
