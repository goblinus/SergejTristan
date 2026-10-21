"""Разбор HTML disclosure.ru и публичного зеркала Интерфакса.

Парсер не ходит в сеть и не пишет в БД. Формат сообщений о существенных фактах
стандартизован Положением Банка России, поэтому поля извлекаются из текста
страницы, а не из хрупких CSS-селекторов конкретной вёрстки.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

DISCLOSURE_BASE_URL = "https://www.disclosure.ru"
EDISCLOSURE_BASE_URL = "https://disclosure.1prime.ru"

_ISIN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")
_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


@dataclass(frozen=True, slots=True)
class DisclosureFeedItem:
    """Ссылка на сообщение из ленты раскрытия."""

    url: str
    title: str
    issuer_name: str | None
    published_at: datetime | None
    message_type: str


@dataclass(frozen=True, slots=True)
class ParsedFeedPage:
    """Результат разбора одной страницы ленты."""

    items: list[DisclosureFeedItem]
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class DisclosureMessageFact:
    """Разобранный сущфакт сообщения о собрании или дате отсечки."""

    url: str
    title: str
    issuer_name: str | None
    inn: str | None
    published_at: datetime | None
    message_type: str
    message_kind: str
    text: str
    meeting_date: date | None
    meeting_type: str | None
    dividend_question: bool
    dividend_period: str | None
    dividend_per_share: Decimal | None
    record_date: date | None
    record_date_kind: str | None
    description: str | None
    isins: tuple[str, ...]


def _fold(value: str) -> str:
    """Приводит текст к нижнему регистру и заменяет ё на е."""
    return value.casefold().replace("ё", "е")


def _clean_text(value: str) -> str:
    """Нормализует пробелы, сохраняя переводы строк для разбора полей."""
    value = value.replace("\xa0", " ").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def message_kind(message_type: str) -> str | None:
    """Определяет вид сообщения по названию сущфакта."""
    value = _fold(message_type)
    if "решения общих собраний" in value:
        return "results"
    if ("проведени" in value or "созыв" in value) and "общего собрания" in value:
        return "meeting"
    if (
        ("дата" in value and "определяются лица" in value)
        or ("дата определения" in value and "фиксации" in value)
    ):
        return "record_date"
    return None


def is_candidate_message_type(message_type: str) -> bool:
    """Нужно ли загружать сообщение этого типа."""
    return message_kind(message_type) is not None


def _dedupe(items: list[DisclosureFeedItem]) -> list[DisclosureFeedItem]:
    seen: set[str] = set()
    result: list[DisclosureFeedItem] = []
    for item in items:
        if item.url in seen:
            continue
        seen.add(item.url)
        result.append(item)
    return result


def parse_disclosure_feed_page(
    html: str, base_url: str = DISCLOSURE_BASE_URL
) -> ParsedFeedPage:
    """Разбирает страницу ленты disclosure.ru (АК&М).

    Каждая ссылка ленты имеет вид `news.shtml?newsisn=...`, а её текст —
    `ДД.ММ.ГГГГ ЧЧ:ММ <эмитент> - <тип сообщения>`. Для перехода на следующую
    страницу источник использует POST-форму с курсором `ts` (YYYYMMDDHHMMSS).
    """
    soup = BeautifulSoup(html, "lxml")
    items: list[DisclosureFeedItem] = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "newsisn=" not in href:
            continue
        text = link.get_text(" ", strip=True)
        match = re.match(r"(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})\s+(.+)", text)
        if match is None:
            continue
        published_at = _parse_datetime(match.group(1), "%d.%m.%Y %H:%M")
        rest = match.group(2).strip()
        issuer_name, separator, message_type = rest.rpartition(" - ")
        if not separator:
            issuer_name, message_type = None, rest
        items.append(
            DisclosureFeedItem(
                url=_urljoin(base_url + "/rus/corpnews/", href),
                title=rest,
                issuer_name=issuer_name.strip() if issuer_name else None,
                published_at=published_at,
                message_type=message_type.strip(),
            )
        )

    cursor_match = re.search(r"elements\['ts'\]\.value\s*=\s*(\d{14})", html)
    return ParsedFeedPage(
        items=_dedupe(items),
        next_cursor=cursor_match.group(1) if cursor_match else None,
    )


def parse_edisclosure_feed_page(
    html: str, base_url: str = EDISCLOSURE_BASE_URL
) -> ParsedFeedPage:
    """Разбирает страницу ленты публичного зеркала Интерфакса."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="news")
    if table is None:
        return ParsedFeedPage(items=[])

    items: list[DisclosureFeedItem] = []
    for row in table.find_all("tr"):
        date_node = row.find("p", class_="date")
        issuer_link = row.find("a", class_="title")
        if date_node is None or issuer_link is None:
            continue

        message_link = None
        for link in row.find_all("a", href=True):
            if link is issuer_link:
                continue
            if link.get("href", "").lower().startswith("/portal"):
                continue
            message_link = link
            break
        if message_link is None:
            continue

        message_type = message_link.get("title") or message_link.get_text(" ", strip=True)
        issuer_name = issuer_link.get_text(" ", strip=True)
        items.append(
            DisclosureFeedItem(
                url=_urljoin(base_url + "/news/", message_link["href"]),
                title=f"{issuer_name} - {message_type}",
                issuer_name=issuer_name,
                published_at=_parse_datetime(
                    date_node.get_text(" ", strip=True), "%d.%m.%Y %H:%M:%S"
                ),
                message_type=message_type.strip(),
            )
        )

    return ParsedFeedPage(items=_dedupe(items))


def parse_message(
    html: str, item: DisclosureFeedItem
) -> DisclosureMessageFact | None:
    """Разбирает страницу сообщения о собрании или дате отсечки.

    Возвращает None, если тип сообщения не относится к календарю. Записи
    с нераспознанными обязательными полями отбрасываются на стадии нормализации.
    """
    soup = BeautifulSoup(html, "lxml")
    text = _clean_text(soup.get_text("\n", strip=True))
    title = _page_title(soup) or item.title
    kind = message_kind(item.message_type)
    if kind is None and not item.message_type.strip():
        kind = message_kind(title)
    if kind is None:
        return None

    meeting_date = _extract_meeting_date(text)
    if meeting_date is None and kind == "results":
        meeting_date = _extract_event_date(text)
    meeting_type = _extract_meeting_type(text)
    record_date, record_date_kind = _extract_record_date(text)
    dividend_question = "дивиденд" in _fold(text)

    return DisclosureMessageFact(
        url=item.url,
        title=item.title,
        issuer_name=_extract_issuer_name(text) or item.issuer_name,
        inn=_extract_inn(text) or _inn_from_url(item.url),
        published_at=item.published_at,
        message_type=item.message_type,
        message_kind=kind,
        text=text,
        meeting_date=meeting_date,
        meeting_type=meeting_type,
        dividend_question=dividend_question,
        dividend_period=_extract_dividend_period(text) if dividend_question else None,
        dividend_per_share=_extract_dividend_amount(text) if dividend_question else None,
        record_date=record_date,
        record_date_kind=record_date_kind,
        description=_extract_description(text, kind),
        isins=tuple(dict.fromkeys(_ISIN_RE.findall(text.upper()))),
    )


def _page_title(soup: BeautifulSoup) -> str | None:
    if soup.title is None:
        return None
    return soup.title.get_text(" ", strip=True) or None


def _urljoin(base: str, href: str) -> str:
    from urllib.parse import urljoin

    return urljoin(base, href)


def _parse_datetime(value: str, fmt: str) -> datetime | None:
    try:
        return datetime.strptime(value.strip(), fmt)
    except ValueError:
        return None


def parse_date(value: str) -> date | None:
    """Извлекает календарную дату из русского текста."""
    value = value.replace("\xa0", " ")
    numeric = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", value)
    if numeric is not None:
        day, month, year = (int(part) for part in numeric.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    words = re.search(r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})", value, re.IGNORECASE)
    if words is not None:
        month = _MONTHS.get(words.group(2).casefold().replace("ё", "е"))
        if month is not None:
            try:
                return date(int(words.group(3)), month, int(words.group(1)))
            except ValueError:
                return None
    return None


def _extract_issuer_name(text: str) -> str | None:
    match = re.search(
        r"Полное фирменное наименование[^\n]*?(?:[:.]\s*|\t+)([^\n].*)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return None
    value = re.split(r"\n\s*\d+\.\d+[.)]?\s", match.group(1), maxsplit=1)[0]
    value = re.sub(r"\s+", " ", value).strip(" .;")
    return value or None


def _extract_inn(text: str) -> str | None:
    match = re.search(r"ИНН[^\n]*?(?<!\d)(\d{10}|\d{12})(?!\d)", text, re.IGNORECASE)
    return match.group(1) if match else None


def _inn_from_url(url: str) -> str | None:
    match = re.search(r"[?&]emid=(\d+)", url, re.IGNORECASE)
    return match.group(1) if match else None


def _extract_meeting_date(text: str) -> date | None:
    """Извлекает дату собрания.

    Для заочного голосования датой собрания считается дата окончания приёма
    бюллетеней. Прочие упоминания «дата проведения» (например, дата оценки)
    не используются, чтобы не подставить дату из юридической ссылки.
    """
    patterns = (
        r"Дата проведения\s+(?:Собрания|Заседания|Заочного\s+голосования|"
        r"внеочередного\s+заочного\s+голосования|общего\s+собрания)"
        r"[^:\n]*[:\t;–—-]\s*([^\n;]+)",
        r"Дата окончания приема бюллетеней[^:\n]*[:\t;–—-]\s*([^\n;]+)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            parsed = parse_date(match.group(1))
            if parsed is not None:
                return parsed
    return None


def _extract_event_date(text: str) -> date | None:
    """Дата наступления события; для итогов собрания совпадает с датой собрания."""
    for line in text.splitlines():
        if "дата наступления события" in _fold(line):
            parsed = parse_date(line)
            if parsed is not None:
                return parsed
    return None


def _extract_meeting_type(text: str) -> str | None:
    patterns = (
        r"Вид собрания\s*[-–—:]\s*([^\n;]+)",
        r"Вид общего собрания[^\n]*?[.:;]\s*([^\n]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match is not None:
            value = _fold(match.group(1))
            if "внеочеред" in value:
                return "extraordinary"
            if "годов" in value:
                return "annual"

    folded = _fold(text)
    if re.search(r"годовое\s+(?:общее\s+)?(?:заседание|собрание)", folded):
        return "annual"
    if re.search(r"внеочередное\s+(?:общее\s+)?(?:заседание|собрание)", folded):
        return "extraordinary"
    return None


def _looks_like_date_start(value: str) -> bool:
    """Отсекает поля, где дата встречается в описании, а не в начале значения."""
    return (
        re.match(
            r"\s*\d{1,2}\s*(?:\.\s*\d{1,2}\s*\.\s*\d{4}|[а-яё]+\s+\d{4})",
            value,
            re.IGNORECASE,
        )
        is not None
    )


def _first_date_match(pattern: str, text: str, kind: str | None) -> tuple[date | None, str | None]:
    for match in re.finditer(pattern, text, re.IGNORECASE):
        value = match.group(1)
        if not _looks_like_date_start(value):
            continue
        parsed = parse_date(value)
        if parsed is not None:
            resolved_kind = kind or _record_date_kind(match.group(0)) or _record_date_kind(text)
            return parsed, resolved_kind
    return None, None


def _last_date(value: str) -> date | None:
    """Возвращает последнюю дату в значении (поле может содержать пояснение)."""
    dates: list[date] = []
    for pattern in (r"\d{1,2}\.\d{1,2}\.\d{4}", r"\d{1,2}\s+[а-яё]+\s+\d{4}"):
        for match in re.finditer(pattern, value, re.IGNORECASE):
            parsed = parse_date(match.group(0))
            if parsed is not None:
                dates.append(parsed)
    return dates[-1] if dates else None


def _extract_section_record_date(text: str) -> tuple[date | None, str | None]:
    """Ищет отсечку в нумерованном пункте 2.x «Дата, на которую определяются лица...»."""
    pattern = (
        r"(?:^|\n)\s*2\.\d+\.?\s*Дата, на которую определяются"
        r"[^:\n]*[:\t;–—-]\s*([^\n]+)"
    )
    for match in re.finditer(pattern, text, re.IGNORECASE):
        parsed = _last_date(match.group(1))
        if parsed is not None:
            return parsed, _record_date_kind(match.group(0))
    return None, None


def _extract_record_date(text: str) -> tuple[date | None, str | None]:
    direct_patterns = (
        (
            r"Дата, на которую определяются\s*\(фиксируются\)\s*лица, имеющие право"
            r" на участие в Собрании\s*:\s*([^\n;]+)",
            "meeting_participation",
        ),
        (
            r"Дата, на которую определяются\s*\(фиксируются\)\s*лица, имеющие право"
            r" на получение дивидендов\s*:\s*([^\n;]+)",
            "dividend_payment",
        ),
        (
            r"Дата, на которую определяются лица, имеющие право на осуществление"
            r" по ним прав\s*:\s*([^\n;]+)",
            None,
        ),
        (
            r"Дата, на которую определяются\s*\(фиксируются\)\s*лица, имеющие право"
            r"[^:\n]*[:\t;–—-]\s*([^\n;]+)",
            None,
        ),
    )
    for pattern, kind in direct_patterns:
        parsed, resolved_kind = _first_date_match(pattern, text, kind)
        if parsed is not None:
            return parsed, resolved_kind

    approved = re.search(
        r"Утвердить\s+([^\n]{0,80}?)\s+датой, на которую определяются лица,"
        r" имеющие право на получение дивидендов",
        text,
        re.IGNORECASE,
    )
    if approved is not None and _looks_like_date_start(approved.group(1)):
        parsed = parse_date(approved.group(1))
        if parsed is not None:
            return parsed, "dividend_payment"

    section_date, section_kind = _extract_section_record_date(text)
    if section_date is not None:
        return section_date, section_kind or _record_date_kind(text)

    return _first_date_match(
        r"Дата, на которую определяются[^:\n]*:\s*([^\n;]+)", text, None
    )


def _record_date_kind(text: str) -> str | None:
    folded = _fold(text)
    if "дивиденд" in folded and any(
        marker in folded for marker in ("получени", "выплат", "доход")
    ):
        return "dividend_payment"
    if ("участ" in folded or "голос" in folded) and "собрани" in folded:
        return "meeting_participation"
    if "дивиденд" in folded:
        return "dividend_payment"
    return None


def _dividend_window(text: str) -> str:
    match = re.search(
        r"выплатить\s+дивиденды|выплате\s+дивидендов|дивиденд", text, re.IGNORECASE
    )
    if match is None:
        return ""
    return text[max(0, match.start() - 200) : match.end() + 900]


def _extract_dividend_period(text: str) -> str | None:
    for source in (_dividend_window(text), text):
        folded = _fold(source)
        if re.search(
            r"за\s+\d{4}\s+год|по итогам\s+\d{4}\s+года|за\s+(?:отчетный\s+)?год",
            folded,
        ):
            return "year"
        if re.search(
            r"(?:за\s+(?:первое\s+|второе\s+|1-е\s+|2-е\s+)?полугодие|"
            r"за\s+(?:6|шесть)\s+месяцев|"
            r"по\s+(?:результатам|итогам)\s+(?:6|шести)\s+месяцев)",
            folded,
        ):
            return "half_year"
        if re.search(
            r"(?:за\s+(?:i|1|первый)\s+квартал|за\s+(?:3|три)\s+месяца|"
            r"по\s+(?:результатам|итогам)\s+(?:3|три|трех|трёх)\s+месяцев)",
            folded,
        ):
            return "quarter"
        if re.search(
            r"(?:за\s+(?:9|девять)\s+месяцев|"
            r"по\s+(?:результатам|итогам)\s+(?:9|девяти)\s+месяцев)",
            folded,
        ):
            return "quarter"
    return None


def _extract_dividend_amount(text: str) -> Decimal | None:
    window = _dividend_window(text) or text
    amount = r"([\d][\d\s]*(?:[.,]\d+)?)"
    patterns = (
        rf"в\s+размере\s+{amount}\s*(?:руб(?:\.|лей|ля)?|₽)\s*"
        r"на\s+(?:одну|каждую)\s+(?:обыкновенную\s+|привилегированную\s+)?акцию",
        rf"{amount}\s*(?:руб(?:\.|лей|ля)?|₽)\s*на\s+(?:одну|каждую)\s+"
        r"(?:обыкновенную\s+|привилегированную\s+)?акцию",
        rf"выплатить\s+дивиденды[^.]{{0,300}}?в\s+размере\s+"
        rf"{amount}\s*(?:руб(?:\.|лей|ля)?|₽)",
        rf"на\s+(?:одну|каждую)\s+(?:обыкновенную\s+|привилегированную\s+)?акцию"
        rf"[^.\n]{{0,80}}?{amount}\s*(?:руб(?:\.|лей|ля)?|₽)",
    )
    for source in (window, text):
        for pattern in patterns:
            match = re.search(pattern, source, re.IGNORECASE)
            if match is not None:
                parsed = _to_decimal(match.group(1))
                if parsed is not None:
                    return parsed
    return None


def _to_decimal(value: str) -> Decimal | None:
    try:
        number = Decimal(value.replace("\xa0", "").replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number < 0:
        return None
    return number


def _extract_description(text: str, kind: str) -> str | None:
    if kind == "meeting":
        match = re.search(
            r"Повестка дня[^\n]*:?\s*\n?(.+?)"
            r"(?:\n\s*(?:\d+\.\d+\.?\s*)?(?:Порядок ознакомления|Порядок сообщения)"
            r"|\n\s*3\.\s*Подпись|\n\s*2\.3\b)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match is not None:
            return _trim(match.group(1))

    if kind == "results":
        blocks = re.split(r"(?=Вопрос\s*№\s*\d+\s*:)", text, flags=re.IGNORECASE)[1:]
        for block in blocks:
            if "дивиденд" in _fold(block):
                return _trim(block)

    window = _dividend_window(text)
    return _trim(window) if window else None


def _trim(value: str) -> str | None:
    value = re.sub(r"\s+", " ", value).strip()
    return value[:4000] or None
