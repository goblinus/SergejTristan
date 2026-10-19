# 2026-10-19 — Схема БД (backend)

## Назначение документа

Физическая схема базы данных MVP по канонической модели system: таблицы `tickers`, `shareholder_meetings`, `record_dates`, `watchlist_items`; типы колонок, ключи, ограничения, индексы, трассировка источника; подход к миграциям.

СУБД — по ADR-0001 (`design/system/adr/`). Для MVP целевой вариант — SQLite (локальная однопользовательская система, файл БД). Схема и ORM-модели проектируются СУБД-нейтрально (обобщённые типы SQLAlchemy: `Integer`, `String`, `Boolean`, `Date`, `DateTime`, `Text`), что оставляет возможность смены диалекта на PostgreSQL без переделки моделей.

См. ER-диаграмму: [2026-10-19_схема-бд_backend.puml](./2026-10-19_схема-бд_backend.puml).

## Общие соглашения

- Суррогатный PK `id INTEGER PRIMARY KEY` во всех таблицах (SQLite rowid; без AUTOINCREMENT-надстроек).
- Даты событий — `DATE` (календарная дата, московское время UTC+3, без времени; см. допущения system).
- Технические метки времени (`fetched_at`, `created_at`) — `DATETIME`, заполняются на стороне Python как timezone-aware UTC.
- Поля трассировки источника (ADR-0003): `source_url TEXT NOT NULL`, `fetched_at DATETIME NOT NULL` — во всех таблицах доменных данных (т.е. во всех, кроме `watchlist_items`).
- Все текстовые значения хранятся в исходной (источниковой) регистровой форме; регистронезависимый поиск реализуется на уровне запросов, а не хранения.

## Таблицы

### tickers — тикеры Московской биржи

| Колонка | Тип | Ограничения | Комментарий |
|---|---|---|---|
| id | INTEGER | PK | |
| ticker | VARCHAR(16) | NOT NULL, UNIQUE | Бизнес-ключ: SECID MOEX (например, `SBER`). Верхний регистр — при нормализации. |
| short_name | VARCHAR(255) | NOT NULL | Краткое наименование бумаги с MOEX. |
| full_name | VARCHAR(512) | NULL | Полное наименование эмитента, если известно. |
| isin | VARCHAR(12) | NULL | ISIN бумаги. |
| board | VARCHAR(16) | NULL | Режим торгов (например, `TQBR`). Информационно. |
| lot_size | INTEGER | NULL | Размер лота. Информационно. |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | FALSE — бумага исчезла из листинга при очередном сборе (снятие с торгов). Записи не удаляются. |
| source_url | TEXT | NOT NULL | URL запроса к источнику (например, эндпоинт MOEX ISS). |
| fetched_at | DATETIME | NOT NULL | Момент последнего успешного сбора записи. |

Индексы:
- `uq_tickers_ticker` — UNIQUE(ticker) — бизнес-ключ upsert.

### shareholder_meetings — собрания акционеров

| Колонка | Тип | Ограничения | Комментарий |
|---|---|---|---|
| id | INTEGER | PK | |
| ticker_id | INTEGER | NOT NULL, FK → tickers.id, ON DELETE RESTRICT | Эмитент. |
| meeting_date | DATE | NOT NULL | Дата проведения собрания. |
| meeting_type | VARCHAR(16) | NOT NULL | `annual` (годовое) или `extraordinary` (внеочередное). Нормализуется скриптами, CHECK в SQL не накладываем (перечень контролируется кодом). |
| dividend_question | BOOLEAN | NOT NULL, DEFAULT TRUE | TRUE — в повестке вопрос о выплате дивидендов. В MVP собираются только такие собрания; поле — задел схемы, фильтр по умолчанию. |
| description | TEXT | NULL | Формулировка вопроса повестки из источника (как есть). |
| source_url | TEXT | NOT NULL | Ссылка на сообщение о собрании в источнике. |
| fetched_at | DATETIME | NOT NULL | |

Бизнес-ключ upsert и ограничение целостности:
- `uq_meetings_business_key` — UNIQUE(ticker_id, meeting_date, meeting_type).

Индексы:
- `ix_meetings_date` — (meeting_date) — выборки календаря `?from&to`;
- FK-индекс (ticker_id) — покрывается префиксом `uq_meetings_business_key`, отдельно не создаётся.

### record_dates — даты дивидендной отсечки

Дата закрытия реестра. Возможны два смысла отсечки, фиксируем их явно колонкой `kind`: закрытие реестра для участия в собрании и закрытие реестра для выплаты дивидендов. «Сторожок» отслеживает записи `kind = 'dividend_payment'`.

| Колонка | Тип | Ограничения | Комментарий |
|---|---|---|---|
| id | INTEGER | PK | |
| ticker_id | INTEGER | NOT NULL, FK → tickers.id, ON DELETE RESTRICT | Эмитент. |
| meeting_id | INTEGER | NULL, FK → shareholder_meetings.id, ON DELETE SET NULL | Связь с собранием, если установлена источником. NULL допустим: дата отсечки может быть собрана из источника, не связывающего её с конкретным собранием. |
| record_date | DATE | NOT NULL | Дата закрытия реестра. |
| kind | VARCHAR(32) | NOT NULL, DEFAULT 'dividend_payment' | `dividend_payment` — отсечка для выплаты дивидендов; `meeting_participation` — отсечка для участия в собрании. |
| source_url | TEXT | NOT NULL | Ссылка на сообщение/страницу источника. |
| fetched_at | DATETIME | NOT NULL | |

Бизнес-ключ upsert:
- `uq_record_dates_business_key` — UNIQUE(ticker_id, record_date, kind).

Индексы:
- `ix_record_dates_date` — (record_date) — календарь и поиск ближайшей даты для сторожков;
- `ix_record_dates_ticker_kind` — (ticker_id, kind) — выборка отсечек тикера.

### watchlist_items — «сторожки» пользователя

Система однопользовательская: таблица без `user_id`; одна строка на отслеживаемый тикер.

| Колонка | Тип | Ограничения | Комментарий |
|---|---|---|---|
| id | INTEGER | PK | |
| ticker_id | INTEGER | NOT NULL, UNIQUE, FK → tickers.id, ON DELETE RESTRICT | Отслеживаемый тикер. UNIQUE — один сторожок на тикер (бизнес-ключ). |
| threshold_days | INTEGER | NOT NULL, DEFAULT 7 | Индивидуальный порог зоны `hot` статуса сторожка в сутках (каноническая шкала `{no_date, far, near, hot, critical, past}`; см. правила расчёта статуса). |
| created_at | DATETIME | NOT NULL | Момент добавления в отслеживание. |

Индексы:
- `uq_watchlist_ticker` — UNIQUE(ticker_id).

Поля `source_url`/`fetched_at` отсутствуют: сущность пользовательская, пишется только API, источника раскрытия у неё нет. Вычисляемые поля (`days_to_cutoff`, `status`) в БД **не хранятся** — см. [2026-10-19_правила-расчёта-статуса-сторожка_backend.md](./2026-10-19_правила-расчёта-статуса-сторожка_backend.md).

## Связи

- `tickers 1 — N shareholder_meetings`;
- `tickers 1 — N record_dates`;
- `shareholder_meetings 1 — N record_dates` (опциональная, `record_dates.meeting_id` NULL-able);
- `tickers 1 — 0..1 watchlist_items`.

`ON DELETE RESTRICT` на доменных FK: в MVP удаление тикеров не предусмотрено (только `is_active = FALSE`), ограничение страхует от случайного каскадного удаления истории.

## Миграции

Зафиксированное решение для MVP: **Alembic**.

- Каталог `backend/migrations/`, конфиг `alembic.ini`, autogenerate от ORM-моделей (`app/models/base.py::Base.metadata`).
- Причина выбора против `create_all`: схема будет меняться уже в ходе работы над MVP (уточнение модели данных от system-designer), а Alembic даёт воспроизводимую историю изменений и единый порядок инициализации БД для API и скриптов; стоимость входа минимальна (зависимость одна, команды две).
- `Base.metadata.create_all` допускается **только в тестах** (быстрый подъём временной БД из схемы без прогона миграций).
- Порядок инициализации рабочей БД: `uv run alembic upgrade head` — до первого запуска API и скриптов.

## Нормализация значений (контракт для скриптов)

- `ticker` — верхний регистр, без пробелов.
- `meeting_type`: годовое/ОСА → `annual`; внеочередное/ВОСА → `extraordinary`.
- Даты — только валидные календарные; запись с нераспарсенной датой не пишется (логируется как ошибка нормализации).
- Повторный сбор тех же данных обновляет `source_url`/`fetched_at` существующей записи (upsert по бизнес-ключу), а не создаёт дубль.

## Связанные документы

- [2026-10-19_архитектура-бэкенда_backend.md](./2026-10-19_архитектура-бэкенда_backend.md)
- [2026-10-19_api-контракт_backend.md](./2026-10-19_api-контракт_backend.md)
- [2026-10-19_спецификация-скриптов-сбора_backend.md](./2026-10-19_спецификация-скриптов-сбора_backend.md)
- [2026-10-19_правила-расчёта-статуса-сторожка_backend.md](./2026-10-19_правила-расчёта-статуса-сторожка_backend.md)
