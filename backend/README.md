# Бэкенд «Дивидендного календаря»

API и офлайн-сбор данных сервиса отслеживания дивидендных событий Московской биржи.
Текущее состояние — каркас: структура слоёв, модели, схемы и контракт эндпоинтов;
репозитории и скрипты сбора пока возвращают заглушки.

## Стек

- Python `>=3.11`, менеджер зависимостей и окружения — `uv`;
- FastAPI + uvicorn (ADR-0002);
- SQLAlchemy 2.x (синхронный), SQLite по умолчанию (ADR-0001);
- Pydantic v2 / pydantic-settings для DTO и конфигурации;
- httpx, beautifulsoup4, lxml — для скриптов сбора (пока не используются).

## Структура

```text
backend/
├── app/
│   ├── main.py            # FastAPI-приложение, /api/v1, /health, /static
│   ├── core/              # Settings, engine/Session, логирование
│   ├── api/               # роутеры: tickers, meetings, record-dates, watchlist
│   ├── services/          # бизнес-логика: статусы, доходность, DSI, сборка DTO
│   ├── repositories/      # доступ к данным (сейчас — заглушки)
│   ├── models/            # ORM-модели SQLAlchemy 2.x
│   └── schemas/           # Pydantic-схемы API
├── alembic.ini            # конфигурация Alembic
├── migrations/            # Alembic: env.py, script.py.mako, versions/001_initial.py
├── scripts/               # CLI-каркасы сбора данных
│   └── ingestion/         # sources/, parsers/, normalize.py, loader.py
├── static/logos/          # курируемые SVG-логотипы (ADR-0006)
└── tests/                 # smoke API, расчёт статусов, доходность и DSI
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
- `DIVCAL_HTTP_RETRIES`.
- 
Все значения имеют умолчания: сервис стартует без `.env` на файле `./divcal.db`.

## API

Все эндпоинты — под `/api/v1`: 

- `GET /tickers`;
- `GET /meetings`;
- `GET /meetings/{id}`;
- `GET /record-dates`;
- `GET/POST /watchlist`;
- `DELETE /watchlist/{ticker}`.

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
записываются и деактивация не выполняется. Остальные скрипты — argparse-каркасы.

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

## Что пока заглушки

- репозитории `tickers`, `meetings`, `record_dates`, `watchlist` — пустые выборки;
- `GET /meetings/{id}` — всегда 404; `POST` и `DELETE /watchlist` — 501;
- сборка `dividend`, `dsi`-связок и `next_meeting_date` в DTO — TODO в сервисах;
- скрипты `fetch_meetings_disclosure`, `fetch_dividend_history_moex`, `sync_logos` —
  без пайплайна fetch/parse/normalize/load;
- `scripts/ingestion/loader.py` — `load_meetings`, `load_record_dates`,
  `load_dividend_metrics` бросают `NotImplementedError`.

Реализованы полностью: `compute_yield`, `calc_status`, `calc_days_to_cutoff`,
`calc_dsi`, миграции Alembic, валидация параметров API, сбор тикеров MOEX ISS
(`fetch_tickers_moex`).

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
