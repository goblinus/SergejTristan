"""Тесты источника истории дивидендов MOEX ISS без обращения к сети."""

from typing import Any

import httpx
import pytest

import scripts.ingestion.sources.moex_iss as moex_iss
from app.core.config import Settings
from scripts.ingestion.sources.moex_iss import (
    MoexFormatSourceError,
    MoexSourceError,
    fetch_dividends,
)

PAYLOAD = {
    "dividends": {
        "columns": ["secid", "isin", "registryclosedate", "value", "currencyid"],
        "data": [
            ["SBER", "RU0009029540", "2025-07-18", 37.64, "RUB"],
            ["SBER", "RU0009029540", "2024-07-18", 33.3, "RUB"],
        ],
    },
    "dividends.cursor": {"columns": ["INDEX", "TOTAL"], "data": [[2, 2]]},
}


def _settings(retries: int = 0) -> Settings:
    return Settings(http_retries=retries, http_timeout_seconds=5)


def _client(handler: Any) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_dividends_returns_raw_payload_and_sends_expected_request() -> None:
    """Успешный ответ возвращается как есть; URL и параметры соответствуют контракту."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=PAYLOAD, request=request)

    with _client(handler) as client:
        payload = fetch_dividends(client, _settings(), "SBER")

    assert payload == PAYLOAD
    assert len(requests) == 1
    request = requests[0]
    assert request.url.scheme == "https"
    assert request.url.host == "iss.moex.com"
    assert request.url.path == "/iss/securities/SBER/dividends.json"
    assert dict(request.url.params) == {"iss.meta": "off"}


def test_fetch_dividends_404_raises_without_retries() -> None:
    """HTTP 404 — недоступность источника без повторных запросов."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(404, json={"error": "not found"}, request=request)

    with _client(handler) as client:
        with pytest.raises(MoexSourceError, match="HTTP 404"):
            fetch_dividends(client, _settings(retries=3), "SBER")

    assert len(requests) == 1


def test_fetch_dividends_500_single_attempt_when_retries_disabled() -> None:
    """При http_retries=0 серверная ошибка завершает запрос после одной попытки."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(500, json={"error": "boom"}, request=request)

    with _client(handler) as client:
        with pytest.raises(MoexSourceError, match="after 1 attempts"):
            fetch_dividends(client, _settings(retries=0), "SBER")

    assert len(requests) == 1


def test_fetch_dividends_500_retried_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """При http_retries=1 серверная ошибка повторяется ровно один раз."""
    requests: list[httpx.Request] = []
    delays: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(503, json={"error": "unavailable"}, request=request)

    monkeypatch.setattr(moex_iss.time, "sleep", delays.append)

    with _client(handler) as client:
        with pytest.raises(MoexSourceError, match="after 2 attempts"):
            fetch_dividends(client, _settings(retries=1), "SBER")

    assert len(requests) == 2
    assert delays == [1]


def test_fetch_dividends_invalid_json_raises_format_error() -> None:
    """Невалидный JSON — ошибка формата источника."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>not json</html>", request=request)

    with _client(handler) as client:
        with pytest.raises(MoexFormatSourceError, match="invalid JSON"):
            fetch_dividends(client, _settings(), "SBER")


def test_fetch_dividends_non_object_json_raises_format_error() -> None:
    """JSON-массив вместо объекта — ошибка формата источника."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"secid": "SBER"}], request=request)

    with _client(handler) as client:
        with pytest.raises(MoexFormatSourceError, match="non-object JSON"):
            fetch_dividends(client, _settings(), "SBER")


@pytest.mark.parametrize("secid", ["", "   ", "\t\n"])
def test_fetch_dividends_rejects_empty_secid(secid: str) -> None:
    """Пустой или пробельный secid отклоняется до сетевого запроса."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=PAYLOAD, request=request)

    with _client(handler) as client:
        with pytest.raises(ValueError, match="secid must not be empty"):
            fetch_dividends(client, _settings(), secid)

    assert requests == []
