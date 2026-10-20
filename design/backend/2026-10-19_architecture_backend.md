# 2026-10-19 — Архитектура бэкенда (backend)

## Назначение документа

Структура Python-приложения бэкенда MVP «Дивидендный календарь»: слои, модули, конфигурация. Отвечает на вопрос: как организован код API-сервиса и скриптов сбора данных.

Основание: ADR-0002 (веб-фреймворк — FastAPI), ADR-0001 (СУБД) в `design/system/adr/`, контейнер «Backend API» и «Data collectors» из [контейнеров и потоков](../system/2026-10-19_контейнеры-и-потоки_system.md).

## Принципы

- **Слоистая архитектура**: `api -> service -> repository -> models (SQLAlchemy)`. Слой ниже ничего не знает о слое выше; направление зависимостей строго сверху вниз.
- **Pydantic-схемы (DTO)** — единственный формат на границе API; ORM-модели наружу не отдаются.
- **Конфигурация через окружение**: один класс `Settings` на `pydantic-settings`, значения — из переменных окружения / `.env`.
- **Доменные данные read-only для API**; единственная пишущая сущность API — «сторожок» (watchlist).
- **Скрипты сбора — отдельный вход** (CLI), разделяющий со служебным кодом API только модели БД, репозитории записи и конфигурацию. Скрипты не импортируют код роутеров.

## Слои

См. диаграмму: [2026-10-19_слои-backend_backend.puml](./2026-10-19_слои-backend_backend.puml).

| Слой | Пакет | Ответственность |
|---|---|---|
| API | `app/api/` | FastAPI-роутеры: разбор запроса, валидация Pydantic, вызов сервиса, формирование ответа и HTTP-кодов ошибок. Без бизнес-логики и SQL. |
| Service | `app/services/` | Бизнес-логика: сборка DTO, вычисление статуса сторожка (см. [правила расчёта статуса](./2026-10-19_правила-расчёта-статуса-сторожка_backend.md)), расчёт дивидендной доходности и отдача DSI (см. [дивидендные метрики](./2026-10-20_dividend-metrics_backend.md)), пагинация, проверки существования тикера. |
| Repository | `app/repositories/` | Доступ к данным через SQLAlchemy: запросы чтения для API, upsert для скриптов. Единственное место SQL/ORM-запросов. |
| Models | `app/models/` | Декларативные ORM-модели SQLAlchemy 2.x по [схеме БД](./2026-10-19_схема-бд_backend.md). |
| Schemas | `app/schemas/` | Pydantic-модели запросов/ответов по [API-контракту](./2026-10-19_api-контракт_backend.md). |
| Core | `app/core/` | Конфигурация (`Settings`), создание engine/Session, логирование, lifespan-приложение. |

## Структура репозитория (backend/)

```text
backend/
├── pyproject.toml            # uv, см. 2026-10-19_зависимости-и-окружение_backend.md
├── .env.example
├── app/
│   ├── main.py               # создание FastAPI-приложения, подключение роутеров, /api/v1
│   ├── core/
│   │   ├── config.py         # Settings (pydantic-settings)
│   │   ├── db.py             # engine, session factory, зависимость get_session
│   │   └── logging.py        # настройка stdlib logging
│   ├── api/
│   │   ├── deps.py           # общие зависимости роутеров (сессия, параметры пагинации)
│   │   ├── tickers.py        # GET /tickers (только список; карточка тикера исключена из MVP, решение Р-8)
│   │   ├── meetings.py       # GET /meetings
│   │   ├── record_dates.py   # GET /record-dates
│   │   └── watchlist.py      # GET/POST/DELETE /watchlist
│   ├── services/
│   │   ├── tickers.py
│   │   ├── calendar.py       # собрания + даты отсечки
│   │   ├── dividends.py      # доходность на чтении, DSI в DTO
│   │   └── watchlist.py      # CRUD + расчёт статуса и next_meeting_date
│   ├── repositories/
│   │   ├── tickers.py
│   │   ├── meetings.py
│   │   ├── record_dates.py
│   │   └── watchlist.py
│   ├── models/               # SQLAlchemy ORM
│   │   ├── base.py           # DeclarativeBase
│   │   ├── ticker.py
│   │   ├── shareholder_meeting.py
│   │   ├── record_date.py
│   │   └── watchlist_item.py
│   └── schemas/              # Pydantic DTO
│       ├── common.py         # Page[...], ошибка
│       ├── ticker.py
│       ├── meeting.py
│       ├── dividend.py       # DividendTerms, DSI-поля
│       ├── record_date.py
│       └── watchlist.py
├── scripts/                  # офлайн-сбор данных, см. спецификацию скриптов
│   ├── fetch_tickers_moex.py
│   ├── fetch_dividends_moex.py
│   ├── sync_logos.py
│   ├── fetch_meetings_disclosure.py
│   └── ingestion/
│       ├── sources/          # адаптеры источников (moex_iss, disclosure)
│       ├── parsers/          # разбор сырых ответов -> канонические DTO
│       ├── normalize.py      # приведение к канонической модели
│       └── loader.py         # идемпотентный upsert через репозитории
├── migrations/               # Alembic
└── tests/
    ├── fixtures/             # сохранённые JSON/HTML ответов источников
    ├── test_parsers.py
    ├── test_loader.py
    └── test_api.py
```

Отличие от предварительной схемы `docs/repo-schema.md`: для MVP убраны `auth`, `notifications`, `ws`, `admin`, Celery/Redis — отсутствуют в объёме MVP (см. границы в обзоре архитектуры system).

## Конфигурация (pydantic-settings)

Один класс `app/core/config.py::Settings` (`BaseSettings`, префикс переменных `DIVCAL_`):

| Переменная | Назначение | Значение по умолчанию |
|---|---|---|
| `DIVCAL_DATABASE_URL` | Строка подключения SQLAlchemy | `sqlite:///./divcal.db` (MVP по ADR-0001) |
| `DIVCAL_LOG_LEVEL` | Уровень логирования | `INFO` |
| `DIVCAL_WATCH_SOON_DAYS` | Граница зоны `near` статуса сторожка (сутки) | `14` |
| `DIVCAL_WATCH_DEFAULT_THRESHOLD_DAYS` | Граница зоны `hot` по умолчанию для нового сторожка | `7` |
| `DIVCAL_HTTP_TIMEOUT_SECONDS` | Таймаут запросов скриптов к источникам | `30` |
| `DIVCAL_HTTP_RETRIES` | Повторные попытки запросов скриптов | `3` |

Секретов в MVP нет (однопользовательская система, внешние API публичные). `Settings` создаётся один раз и пробрасывается в зависимости.

## Работа с БД

- SQLAlchemy 2.x, синхронный engine (нагрузка MVP минимальна; async не требуется).
- Зависимость `get_session` (FastAPI Depends) отдаёт `Session` на запрос с автоматическим закрытием; транзакция — на уровне сервиса записи сторожка.
- Скрипты сбора создают собственную сессию напрямую из `app/core/db.py` (общий код подключения с API, копирования нет).
- Схема и миграции — Alembic, см. [схему БД](./2026-10-19_схема-бд_backend.md).

## Связь со скриптами сбора

- Общее: `app/models`, `app/repositories` (функции upsert), `app/core` (конфиг, БД, логирование), канонические Pydantic-DTO нормализации (`scripts/ingestion/normalize.py` — отдельные DTO, не API-схемы).
- Не общее: роутеры, сервисы чтения, API-схемы. Скрипты не поднимают HTTP-сервер.
- CLI и пайплайн: [2026-10-19_спецификация-скриптов-сбора_backend.md](./2026-10-19_спецификация-скриптов-сбора_backend.md).

## Что осознанно не проектируется (вне MVP)

- Аутентификация, авторизация, многопользовательность.
- Фоновые задачи внутри API (планировщик — планировщик ОС: cron/Task Scheduler, см. контейнеры system).
- WebSocket, уведомления, кэширование ответов, rate limiting.

## Связанные документы

- [2026-10-19_схема-бд_backend.md](./2026-10-19_схема-бд_backend.md)
- [2026-10-19_api-контракт_backend.md](./2026-10-19_api-контракт_backend.md)
- [2026-10-19_спецификация-скриптов-сбора_backend.md](./2026-10-19_спецификация-скриптов-сбора_backend.md)
- [2026-10-19_зависимости-и-окружение_backend.md](./2026-10-19_зависимости-и-окружение_backend.md)
- [2026-10-19_правила-расчёта-статуса-сторожка_backend.md](./2026-10-19_правила-расчёта-статуса-сторожка_backend.md)
