# Бэкенд «Дивидендного календаря»

API и офлайн-сбор данных сервиса отслеживания дивидендных событий Московской биржи.
Реализованы все эндпоинты API (`/tickers`, `/meetings`, `/record-dates`, `/watchlist`),
сбор тикеров с MOEX ISS, собраний/дат отсечки из disclosure и синхронизация
логотипов эмитентов. Не реализован сбор истории дивидендов (расчёт DSI) — см.
раздел «Что пока не реализовано».

## Стек

- Python `>=3.11`, менеджер зависимостей и окружения — `uv`;
- FastAPI + uvicorn (ADR-0002);
- SQLAlchemy 2.x (синхронный), SQLite по умолчанию (ADR-0001);
- Pydantic v2 / pydantic-settings для DTO и конфигурации;
- httpx, beautifulsoup4, lxml — загрузка и разбор HTML источников раскрытия.

## Структура

```text
backend/
├── app/
│   ├── main.py            # FastAPI-приложение, /api/v1, /health, /static
│   ├── core/              # Settings, engine/Session, логирование
│   ├── api/               # роутеры: tickers, meetings, record-dates, watchlist
│   ├── services/          # бизнес-логика: календарь, сторожки, статусы, доходность, DSI
│   ├── repositories/      # доступ к данным: чтение API, CRUD сторожков, upsert для скриптов
│   ├── models/            # ORM-модели SQLAlchemy 2.x
│   └── schemas/           # Pydantic-схемы API
├── alembic.ini            # конфигурация Alembic
├── migrations/            # Alembic: env.py, script.py.mako, versions/001_initial.py
├── assets/logos/          # курируемые SVG-логотипы {TICKER}.svg (ADR-0006)
├── scripts/               # CLI сбора данных
│   └── ingestion/         # sources/, parsers/, normalize.py, loader.py
├── static/logos/          # раздача SVG-логотипов по /static/logos, наполняется
│                          # скриптом sync_logos
└── tests/                 # API, статусы сторожков, дивидендные метрики, парсеры
                           # и нормализация disclosure/MOEX, loader, CLI сбора
```

## Первый запуск

Выполняется из каталога `backend/`:

```bash
uv sync                                      # окружение и зависимости
uv run alembic upgrade head                  # создание/обновление схемы БД
uv run uvicorn app.main:app --reload         # dev-сервер: http://127.0.0.1:8000
```
Документация API: `http://127.0.0.1:8000/docs`.

## Тесты и линт

```bash
uv run pytest
uv run ruff check .
```

## Конфигурация

Переменные окружения с префиксом `DIVCAL_` (шаблон — `.env.example`):

- `DIVCAL_DATABASE_URL`;
- `DIVCAL_LOG_LEVEL`, `DIVCAL_WATCH_SOON_DAYS`;
- `DIVCAL_WATCH_DEFAULT_THRESHOLD_DAYS`;
- `DIVCAL_HTTP_TIMEOUT_SECONDS`;
- `DIVCAL_HTTP_RETRIES`;
- `DIVCAL_DISCLOSURE_LOOKBACK_DAYS` — глубина повторного обхода ленты disclosure (3 дня).

Все значения имеют умолчания: сервис стартует без `.env` на файле `./divcal.db`.

## API

Все эндпоинты — под `/api/v1`:

- `GET /tickers` — активные тикеры, поиск `q`, пагинация;
- `GET /meetings` — собрания с дивидендным вопросом (`from`, `to`, `ticker`);
- `GET /meetings/{id}` — карточка собрания;
- `GET /record-dates` — даты отсечки (`from`, `to`, `ticker`, `kind`);
- `GET /watchlist` — сторожки с вычисленными на чтении полями;
- `POST /watchlist` — добавить тикер в отслеживание (идемпотентно: 201 —
  создан, 200 — уже был, 404 — тикер не найден);
- `DELETE /watchlist/{ticker}` — снять с отслеживания (204 / 404).

Все списки возвращаются в конверте `Page` (`items`, `page`, `page_size`, `total`);
`page_size` — 1..100. Ошибки валидации — 422.

### Событие сторожка в `GET /watchlist`

Дата ближайшего будущего события определяется приоритетом «отсечка → собрание»
(решение владельца от 2026-10-22):

1. ближайшая отсечка `dividend_payment` с `record_date >= today`; `next_meeting_date`
   и `next_dividend` берутся у связанного с ней собрания;
2. если таких отсечек нет — ближайшее собрание с `dividend_question = true`
   и `meeting_date >= today`: в этом режиме `next_record_date = next_meeting_date =
   meeting_date`, `next_dividend` — дивидендные условия этого собрания;
3. если будущих событий нет — `next_record_date`/`next_meeting_date`/`days_to_event`
   равны `null`; `status = past`, когда есть прошедшие события (отсечка
   `dividend_payment` или собрание с дивидендным вопросом), иначе `status = no_date`.

`status` считается от даты события: `critical` — 0 дней, `hot` — 1..`threshold_days`,
`near` — до `DIVCAL_WATCH_SOON_DAYS`, `far` — дальше. Сортировка каноническая:
сначала датированные сторожки по дате события, затем `no_date`, затем `past`
(внутри групп — по тикеру).

Контракт — `design/backend/2026-10-19_api-contract_backend.md`.

## Скрипты сбора

```bash
uv run python -m scripts.fetch_tickers_moex [--dry-run] [--verbose]
uv run python -m scripts.fetch_meetings_disclosure [--source disclosure|e-disclosure] [--dry-run] [--verbose]
uv run python -m scripts.fetch_dividend_history_moex [--dry-run] [--verbose]
uv run python -m scripts.sync_logos [--dry-run] [--verbose]
```

`fetch_tickers_moex` реализован полностью: постраничная загрузка MOEX ISS с
повторами запросов (таймаут и число попыток — из конфигурации), нормализация,
идемпотентный upsert в `tickers` и деактивация бумаг доски TQBR, исчезнувших из
листинга. Повторный запуск не создаёт дублей; при сбое источника данные не
записываются и деактивация не выполняется.

`fetch_meetings_disclosure` реализован полностью: читает ленту сообщений
disclosure.ru (АК&М), отбирает объявления собраний, итоги собраний и сообщения
о дате отсечки, разбирает даты/тип собрания/период и сумму дивиденда, сопоставляет
эмитента с активным тикером по ISIN или наименованию и идемпотентно пишет
`shareholder_meetings` и `record_dates`. Резервный источник `--source e-disclosure`
использует публичное зеркало Интерфакса `disclosure.1prime.ru`: сам
`e-disclosure.ru` блокирует автоматические запросы анти-бот-защитой.
`--dry-run` проходит весь пайплайн без записи в БД. Коды возврата: 0 — успех,
1 — все источники/БД недоступны, 2 — часть сообщений не загрузилась или не
разобралась.

`sync_logos` реализован полностью: читает курируемые SVG из `assets/logos/`
(файлы `{TICKER}.svg`, тикер в имени сравнивается без учёта регистра),
проверяет, что файл — XML с корневым элементом `<svg>`, копирует валидные
ассеты в `static/logos/{TICKER}.svg` только при отсутствии или изменении
содержимого и проставляет `tickers.logo_url = "/static/logos/{TICKER}.svg"`
для всех тикеров (включая неактивные); тикерам без валидного ассета значение
сбрасывается в `NULL` (UI показывает монограмму). Обновляются только строки,
где значение отличается. Битый или не-SVG файл — WARNING, тикер считается
«без ассета», остальные обрабатываются. `--dry-run` выполняет валидацию и
подсчёт без копирования файлов и записи в БД. Защита от массового обнуления:
отсутствующий или пустой (без `.svg`) каталог источника — ERROR, код 1,
БД и файлы не изменяются. Коды возврата: 0 — успех, в том числе при частичных
WARNING; 1 — фатальная ошибка источника, записи статики или БД. Итоговая строка
лога содержит счётчики ассетов (найдено/валидно/битых), тикеров с логотипом,
очищенных и обновлённых записей, скопированных файлов и признак `dry_run`.

## Миграции

Схема БД управляется Alembic: конфиг — `alembic.ini`, окружение — `migrations/env.py`,
ревизии — `migrations/versions/`. URL БД берётся из `DIVCAL_DATABASE_URL`, metadata —
из ORM-моделей `app.models`.

```bash
uv run alembic upgrade head      # применить все ревизии
uv run alembic current           # текущая ревизия
uv run alembic upgrade head --sql  # offline-SQL без подключения к БД
```

Автоматически при старте API миграции не применяются — только отдельной командой.

## Что нужно доделать

| № | Задача | Где | Блокер / зависимость | Приоритет |
|---|---|---|---|---|
| 1 | Парсер истории дивидендов MOEX (блок `dividends`) | `scripts/ingestion/parsers/moex_dividends.py` | эндпоинт `/iss/securities/{secid}/dividends.json` сейчас не отдаёт блок `dividends` (проверено 2026-10-22); парсер должен переживать его отсутствие | Высокий |
| 2 | Агрегация годовых DPS за 5 лет → `NormalizedDividendMetrics` | `scripts/ingestion/normalize.py` | п. 1 | Высокий |
| 3 | Запись снапшота DSI: `update_dsi()` (`dsi`, `dsi_updated_at`) | `app/repositories/tickers.py` | — | Высокий |
| 4 | `load_dividend_metrics()` вместо `NotImplementedError` | `scripts/ingestion/loader.py` | п. 3 | Высокий |
| 5 | Оркестрация `fetch_dividend_history_moex` (`--dry-run`, коды 0/1/2) | `scripts/fetch_dividend_history_moex.py` | п. 1–4 | Высокий |
| 6 | Тесты DSI-пайплайна: парсер, агрегация, порог «< 3 лет → null», загрузчик, CLI | `tests/` | п. 1–5 | Высокий |
| 7 | Выбор источника истории дивидендов | `design/backend/` | старый MOEX ISS не отдаёт данные; варианты: disclosure.ru (бесплатно, парсинг сообщений), MOEX CCI `/iss/cci/corp-actions/dividends` (подписка), API НРД (договор) | Высокий |
| 8 | Планировщик ежедневного сбора (cron / Планировщик Windows) | вне кода API | настраивается при эксплуатации | Средний |
| 9 | Наполнение справочника логотипов | `assets/logos/` | сейчас 6 из 510 тикеров; остальным показывается монограмма | Средний |
| 10 | Синхронизировать `canonical-data-model_system.md` с fallback «отсечка → собрание» | `design/system/` | решение system-designer | Низкий |
| 11 | Актуализировать дерево `tests/` в `architecture_backend.md` | `design/backend/` | — | Низкий |
| 12 | Уточнить имя `next_record_date` (в fallback содержит дату собрания) | `design/backend/`, `design/frontend/`, `design/ui/` | решение владельца/system-designer | Низкий |

Итог: DSI в API и UI уже отдаётся, но `tickers.dsi` пуст, пока не реализован сбор истории дивидендов (п. 1–7).

Реализованы полностью: все эндпоинты API (`GET /tickers`, `GET /meetings`,
`GET /meetings/{id}`, `GET /record-dates`, `GET/POST /watchlist`,
`DELETE /watchlist/{ticker}`), вычисляемые поля сторожка (`next_record_date`,
`next_meeting_date`, `next_dividend`, `days_to_event`, `status`, `dsi`) с выбором
события «отсечка → fallback на собрание», `compute_yield`, `calc_status`,
`calc_days_to_event`, `calc_dsi`, миграции Alembic, валидация параметров API,
сбор тикеров MOEX ISS (`fetch_tickers_moex`), собраний/отсечек disclosure
(`fetch_meetings_disclosure`) и синхронизация логотипов (`sync_logos`).

## Источники истины

- `design/backend/2026-10-19_architecture_backend.md`
- `design/backend/2026-10-19_api-contract_backend.md`
- `design/backend/2026-10-19_database-schema_backend.md`
- `design/backend/2026-10-19_dependencies-and-env_backend.md`
- `design/backend/2026-10-19_alarm-date-calculation-rules_backend.md`
- `design/backend/2026-10-20_dividend-metrics_backend.md`
- `design/backend/2026-10-19_collect-scripts-specifications_backend.md`
- ADR: `design/system/adr/2026-10-19_adr-0001-dbms-choice_system.md`,
  `2026-10-19_adr-0002-backend-web-framework_system.md`,
  `2026-10-20_adr-0005-dividend-metrics_system.md`,
  `2026-10-20_adr-0006-company-logos_system.md`.
