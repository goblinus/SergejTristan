"""Адаптер MOEX ISS: список бумаг и история дивидендов с повторами запросов."""

import logging
import time
from typing import Any

import httpx

from app.core.config import Settings
from scripts.ingestion.parsers.moex_tickers import (
    DEFAULT_BOARD,
    MoexFormatError,
    MoexSecurity,
    parse_securities_page,
)

BASE_URL = "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json"
DIVIDENDS_URL = "https://iss.moex.com/iss/securities/{secid}/dividends.json"

logger = logging.getLogger(__name__)


class MoexSourceError(RuntimeError):
    """Источник недоступен или вернул данные в неожиданном формате."""


class MoexFormatSourceError(MoexSourceError):
    """Ответ источника не соответствует ожидаемой структуре."""


def _request_json(
    client: httpx.Client,
    url: str,
    settings: Settings,
    *,
    params: dict[str, Any] | None = None,
    context: str = "",
) -> dict[str, Any]:
    """Загружает JSON-объект с повторами на сетевых ошибках, 5xx и 429.

    HTTP 4xx (кроме 429) не повторяются. Задержка между попытками —
    1, 2, 4, ... секунды. `context` добавляется в сообщения об ошибках
    и логи повторов (например, `start=0` или `secid=SBER`).
    """
    where = f"url={url}" + (f" {context}" if context else "")
    attempt = 0

    while True:
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise MoexFormatSourceError(
                    f"MOEX ISS returned a non-object JSON for {where}"
                )
            return payload
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if 400 <= status < 500 and status != 429:
                raise MoexSourceError(f"MOEX ISS HTTP {status} for {where}") from exc
            if attempt >= settings.http_retries:
                raise MoexSourceError(
                    f"MOEX ISS HTTP {status} for {where} after {attempt + 1} attempts"
                ) from exc
            delay = 2**attempt
            logger.warning(
                "retry %s attempt=%d status=%d delay=%ds",
                where,
                attempt + 1,
                status,
                delay,
            )
            attempt += 1
            time.sleep(delay)
        except httpx.RequestError as exc:
            if attempt >= settings.http_retries:
                raise MoexSourceError(
                    f"MOEX ISS request failed for {where} after {attempt + 1} attempts: {exc}"
                ) from exc
            delay = 2**attempt
            logger.warning(
                "retry %s attempt=%d error=%s delay=%ds",
                where,
                attempt + 1,
                type(exc).__name__,
                delay,
            )
            attempt += 1
            time.sleep(delay)
        except ValueError as exc:
            raise MoexFormatSourceError(
                f"MOEX ISS returned invalid JSON for {where}: {exc}"
            ) from exc


def _request_page(client: httpx.Client, start: int, settings: Settings) -> dict[str, Any]:
    """Загружает страницу списка бумаг с повторами запросов."""
    params = {"iss.meta": "off", "start": start}
    return _request_json(client, BASE_URL, settings, params=params, context=f"start={start}")


def fetch_dividends(
    client: httpx.Client, settings: Settings, secid: str
) -> dict[str, Any]:
    """Загружает историю дивидендов эмитента: /iss/securities/{secid}/dividends.json.

    Возвращает сырой JSON-объект ответа; разбор таблицы `dividends` выполняет
    парсер. Пустой или пробельный `secid` отклоняется до запроса, чтобы
    не уходить на URL без тикера.
    """
    code = secid.strip()
    if not code:
        raise ValueError("secid must not be empty")

    payload = _request_json(
        client,
        DIVIDENDS_URL.format(secid=code),
        settings,
        params={"iss.meta": "off"},
        context=f"secid={code}",
    )
    logger.debug("stage=fetch_dividends secid=%s", code)
    return payload


def fetch_securities(
    client: httpx.Client, settings: Settings, board: str = DEFAULT_BOARD
) -> list[MoexSecurity]:
    """Загружает все страницы со списком бумаг и возвращает факты по доске board."""
    facts: dict[str, MoexSecurity] = {}
    start = 0

    while True:
        payload = _request_page(client, start, settings)
        try:
            page = parse_securities_page(payload, board=board)
        except MoexFormatError as exc:
            raise MoexFormatSourceError(f"unexpected MOEX ISS response: {exc}") from exc

        for fact in page.facts:
            facts[fact.secid] = fact

        if page.row_count == 0:
            break

        # Эндпоинт securities.json отдаёт весь список сразу и игнорирует start
        # (cursor/TOTAL при этом отсутствует). Постраничный обход выполняем
        # только когда источник сообщает общее число строк.
        if page.total is None:
            logger.debug("no cursor TOTAL: treating page as complete")
            break

        start += page.row_count
        if start >= page.total:
            break

    logger.info("stage=fetch fetched=%d board=%s", len(facts), board)
    return list(facts.values())
