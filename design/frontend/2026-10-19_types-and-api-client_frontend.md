# Типы и API-клиент фронтенда (MVP)

Дата: 2026-10-19. Статус: проект, раунд 3 (доработка по ревью system-designer
раунда 2; решения Р-1, Р-4, Р-5, Р-6, Р-8, Р-10). Обновлено 2026-10-20:
дивидендные метрики добавлены по ADR-0005 (Р-5 пересмотрен в этой части).

Закрываемый вопрос: **типизированная стыковка с бэкендом без рассинхрона** —
TypeScript-интерфейсы DTO, зеркалирующие опубликованный API-контракт бэкенда
(`design/backend/2026-10-19_api-контракт_backend.md` с правками Р-4/Р-6 из
`design/system/2026-10-19_ревью-спецификаций-раунд-1_system.md`),
HTTP-клиент, единая обработка ошибок и состояний загрузки.

**Решения раунда 1, закрывшие прежние открытые вопросы:**
- JSON-поля — `snake_case`, мэппинг-кейс на клиенте **не нужен** (Р-1):
  TypeScript-типы повторяют JSON как есть.
- Формат ошибок — `{ "detail": string }` (FastAPI), фиксируется в §3.1.
- Списковые ответы — конверт `Page { items, page, page_size, total }` (Р-6).
- Поля трассировки `fetched_at` (в `Ticker`/`Meeting`/`RecordDate`) и
  `source_url` (в `Meeting`) добавлены в API для индикатора свежести и
  ссылки на источник (Р-6).
- Дивидендные метрики (период выплат, сумма на акцию, доходность, DSI) добавлены
  в MVP по ADR-0005 и входят в DTO; `last_trading_day` (учёт T+1) по-прежнему
  вне MVP (Р-5).

## 1. Модель данных (`src/types/`)

Все даты на транспортном уровне — строки ISO 8601. Дни без времени —
`YYYY-MM-DD` (календарные даты домена, московское время); метки времени —
ISO 8601 с зоной UTC (`2026-10-19T12:00:00Z`).

### 1.1. Конверт пагинации `Page<T>`

```ts
// types/page.ts
export interface Page<T> {
  items: T[];
  page: number;      // >= 1
  page_size: number; // 1..100
  total: number;
}
```

Все эндпоинты списков возвращают `Page`. «Голых» массивов в API нет.

### 1.2. `Ticker` — ценная бумага MOEX

```ts
// types/ticker.ts
export interface Ticker {
  /** Торговый код (SECID MOEX), верхний регистр: "SBER" */
  ticker: string;
  /** Краткое название эмитента: "Сбербанк" */
  short_name: string;
  full_name: string | null;
  isin: string | null;
  board: string | null;
  lot_size: number | null;
  /** URL/путь к логотипу эмитента; null — нет (UI показывает монограмму) */
  logo_url: string | null;
  is_active: boolean;
  /** Метка времени последнего обновления записи сборщиком (Р-6) */
  fetched_at: string; // ISO datetime UTC
}
```

Идентификация тикера — по коду `ticker` (SECID), отдельного числового `id`
на клиенте нет и не требуется.

### 1.3. `RecordDate` — дата отсечки

```ts
// types/record-date.ts
export type RecordDateKind = 'dividend_payment' | 'meeting_participation';

export interface RecordDate {
  ticker: string;
  /** Дата закрытия реестра (день без времени) */
  record_date: string; // YYYY-MM-DD
  kind: RecordDateKind;
  /** id связанного собрания; null — отсечка без собрания */
  meeting_id: number | null;
  fetched_at: string; // ISO datetime UTC (Р-6)
}
```

Поле `last_trading_day` (учёт T+1) — вне MVP (Р-5), в типе отсутствует.

### 1.4. `Meeting` — собрание акционеров

```ts
// types/meeting.ts
export type MeetingType = 'annual' | 'extraordinary';

/** Вложенная отсечка внутри Meeting (сокращённая форма RecordDate) */
export interface MeetingRecordDate {
  record_date: string; // YYYY-MM-DD
  kind: RecordDateKind;
}

export interface Meeting {
  id: number;
  ticker: string;
  short_name: string;
  /** Логотип эмитента; null — нет (UI показывает монограмму) */
  logo_url: string | null;
  /** Дата собрания (день без времени) */
  meeting_date: string; // YYYY-MM-DD
  meeting_type: MeetingType;
  /** Описание/повестка; null — не опубликовано */
  description: string | null;
  /** Связанная отсечка dividend_payment; null — отсечка ещё не назначена */
  record_date: MeetingRecordDate | null;
  /** Дивидендные условия собрания; null — не раскрыты */
  dividend: DividendTerms | null;
  /** DSI эмитента, целое 0..100; null — недостаточно истории */
  dsi: number | null;
  /** Ссылка на первоисточник (раскрытие эмитента); null — неизвестна (Р-6) */
  source_url: string | null;
  fetched_at: string; // ISO datetime UTC (Р-6)
}
```

Доходность (`yield_percent`) вычисляется на бэкенде к последней цене акции и
приходит готовой; фронтенд её не пересчитывает.

### 1.5. `WatchlistItem` — сторожок

```ts
// types/watchlist.ts
/** Каноническая шкала статусов (Р-4); вычисляется на сервере */
export type WatchStatus = 'no_date' | 'far' | 'near' | 'hot' | 'critical' | 'past';

export interface WatchlistItem {
  ticker: string;
  short_name: string;
  /** Логотип эмитента; null — нет */
  logo_url: string | null;
  /** Персональный порог зоны hot, дней (1..365, по умолчанию 7) */
  threshold_days: number;
  /** Когда пользователь поставил сторожок */
  created_at: string; // ISO datetime UTC
  /** Ближайшая (сегодня или позже) отсечка dividend_payment; null — нет */
  next_record_date: string | null; // YYYY-MM-DD
  /** Дата собрания, связанного с next_record_date; null — связь не установлена */
  next_meeting_date: string | null; // YYYY-MM-DD
  /** Дней от текущей даты сервера до next_record_date; null вместе с ним */
  days_to_cutoff: number | null;
  /** Статус по шкале Р-4; вычисляется на чтении, хранения в БД нет */
  status: WatchStatus;
  /** Дивидендные условия ближайшей отсечки; null — нет данных */
  next_dividend: DividendTerms | null;
  /** DSI эмитента, целое 0..100; null — недостаточно истории */
  dsi: number | null;
}
```

Расчёт статуса и «дней до отсечки» — ответственность бэкенда (Р-3).
Фронтенд не пересчитывает: UI-компонент `DeadlineIndicator` (C-07)
отображает готовую пару `{ status, days_to_cutoff }` по таблице маппинга
из `design/ui/2026-10-19_индикация-сроков_ui.md`.

### 1.6. Тело создания сторожка

```ts
// types/watchlist.ts
export interface WatchlistCreate {
  /** Код тикера; бэкенд нормализует (trim, верхний регистр) */
  ticker: string;
  /** Необязателен; при отсутствии — дефолт конфигурации бэкенда (7) */
  threshold_days?: number; // 1..365
}
```

### 1.7. Дивидендные метрики `DividendTerms`

```ts
// types/dividend.ts
export type DividendPeriod = 'year' | 'half_year' | 'quarter';

/** Дивидендные условия одной выплаты (собрания / ближайшей отсечки сторожка) */
export interface DividendTerms {
  /** Период, за который выплачиваются дивиденды; null — не раскрыт */
  period: DividendPeriod | null;
  /** Сумма на одну акцию, ₽; null — не раскрыта */
  amount_per_share: number | null;
  /** Дивидендная доходность к последней цене, %; null — нет цены/суммы */
  yield_percent: number | null;
}
```

`yield_percent` и `dsi` — серверные вычисляемые значения: клиент показывает их
как есть и не пересчитывает. Форматирование (валюта, проценты, «—» для `null`)
— в [2026-10-20_dividend-metrics_frontend.md](./2026-10-20_dividend-metrics_frontend.md).

## 2. API-контракт

Base path: `/api/v1`. Аутентификации нет (однопользовательский MVP).
Адресация в dev (Р-10): порт бэкенда по умолчанию — **8000**, Vite-proxy
`/api` → `http://localhost:8000` сохраняет путь (см. также документ по сборке).

Параметры пагинации всех списков: `page` (>=1, по умолчанию 1),
`page_size` (1..100, по умолчанию 50). Ответ — `Page<T>`.

| Метод | Путь | Query | Тело | Ответ | Коды |
|-------|------|-------|------|-------|------|
| GET | `/tickers` | `q?`, `page`, `page_size` | — | `Page<Ticker>` | 200 / 422 |
| GET | `/meetings` | `from?`, `to?`, `ticker?`, `page`, `page_size` | — | `Page<Meeting>` | 200 / 422 |
| GET | `/meetings/{id}` | — | — | `Meeting` | 200 / 404 |
| GET | `/record-dates` | `from?`, `to?`, `ticker?`, `kind?`, `page`, `page_size` | — | `Page<RecordDate>` | 200 / 422 |
| GET | `/watchlist` | `page`, `page_size` | — | `Page<WatchlistItem>` | 200 |
| POST | `/watchlist` | — | `WatchlistCreate` | `WatchlistItem` | 201 (создан) / 200 (идемпотентный повтор) / 404 / 422 |
| DELETE | `/watchlist/{ticker}` | — | — | пустое | 204 / 404 |

Примечания к контракту:
- `GET /tickers`: `q` — регистронезависимая подстрока по `ticker` и
  `short_name`; возвращаются только `is_active = true`; сортировка `ticker` ASC.
  Отдельного эндпоинта карточки тикера нет: `GET /tickers/{ticker}` и тип
  `TickerDetails` упразднены решением Р-8 (экрана-потребителя в MVP нет,
  автодополнение использует `GET /tickers?q`).
- `GET /meetings`: дефолт периода — `[сегодня, сегодня + 90 дней]`;
  `from <= to`, иначе 422. Возвращаются собрания с вопросом о дивидендах.
- `GET /meetings/{id}` — нужен deep-link модала деталей `?meeting=<id>` после
  перезагрузки страницы (Р-6). Отдельного экрана собрания нет — только модал.
- `GET /record-dates`: `kind` по умолчанию `dividend_payment` — именно с ним
  календарь запрашивает отсечки (в т.ч. без связанных собраний, Р-6).
- `POST /watchlist` идемпотентен: повторный вызов с тем же тикером не создаёт
  дубль, возвращает 200 с текущим объектом (обновляя `threshold_days`, если
  передан). Этим пользуется undo в Snackbar после снятия сторожка (замечание
  frontend-4): «Отменить» = повторный `POST /watchlist` с тем же телом.
- `DELETE /watchlist/{ticker}` — по коду тикера, не по id записи.
- `Meeting.dividend`, `Meeting.dsi`, `WatchlistItem.next_dividend`,
  `WatchlistItem.dsi` — поля ADR-0005. `dividend`/`next_dividend` равны
  `null`, если условия не раскрыты; внутри объекта отдельные поля тоже
  допускают `null`. `yield_percent` считается бэкендом, `dsi` — снапшот
  эмитента.

## 3. HTTP-клиент (`src/api/http.ts`)

- Обёртка над нативным `fetch`. Внешние HTTP-библиотеки (axios) не
  используются: запросов мало, interceptors не нужны, зависимости минимальны.
- Функция `request<T>(method, path, { body?, params? })`:
  - подставляет `VITE_API_BASE_URL` (по умолчанию `/api`);
  - сериализует `params` в query string (пропускает `undefined`);
  - `Content-Type: application/json` при наличии body;
  - таймаут 10 с через `AbortSignal.timeout()`;
  - `response.ok` → парсинг JSON → `T` (204 → `undefined`);
  - иначе → нормализация в `ApiError` и `throw`.

### 3.1. Ошибки (`src/api/errors.ts`)

```ts
type ApiErrorKind = 'network' | 'timeout' | 'http' | 'parse';

class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null; // http-статус для kind='http'
  readonly body: unknown;         // тело ответа, если JSON распарсился
}
```

Тело ошибки бэкенда — формат FastAPI:
- `{ "detail": "ticker not found" }` для 404/500 — человекочитаемое
  сообщение берётся из `detail`;
- 422 — `detail` является массивом объектов `{ loc, msg, type }`
  (автовалидация Pydantic); для UI сводится к первому `msg`, тело целиком
  остаётся в `ApiError.body` для отладки.

## 4. Эндпоинт-слой (`src/api/endpoints/`)

Один модуль на ресурс; только тонкие функции без состояния:

```ts
// api/endpoints/meetings.ts (скелет)
export function getMeetings(params: { from?: string; to?: string; ticker?: string; page?: number; page_size?: number })
  : Promise<Page<Meeting>> { /* GET /meetings */ }

export function getMeeting(id: number)
  : Promise<Meeting> { /* GET /meetings/{id} */ }
```

```ts
// api/endpoints/record-dates.ts (скелет)
export function getRecordDates(params: { from?: string; to?: string; ticker?: string; kind?: RecordDateKind; page?: number; page_size?: number })
  : Promise<Page<RecordDate>> { /* GET /record-dates */ }
```

```ts
// api/endpoints/watchlist.ts (скелет)
export function addToWatchlist(body: WatchlistCreate)
  : Promise<{ item: WatchlistItem; created: boolean }> { /* 201 → created=true, 200 → false */ }

export function removeFromWatchlist(ticker: string)
  : Promise<void> { /* DELETE /watchlist/{ticker} → 204 */ }
```

Правила:
- Тип возврата всегда DTO из `types/`, «голые» `any`/`unknown` наружу не
  выходят.
- Мэппинга имён полей нет — типы повторяют `snake_case` JSON контракта (Р-1).
  Единственная трансформация на этом слое — различие 200/201 в
  `addToWatchlist` (флаг `created` для Snackbar) и `undefined` для 204.
- Кэширования в этом слое нет — оно в композаблах.

## 5. Состояния загрузки

Унифицированный результат композаблов (см. также
2026-10-19_управление-состоянием_frontend.md):

```ts
interface AsyncState<T> {
  data: Ref<T | null>;
  isLoading: Ref<boolean>;
  error: Ref<ApiError | null>;
  reload: () => Promise<void>;
}
```

Инварианты для UI: `isLoading` → скелетоны (C-11); `error` → StateBanner
error (C-13) с «Повторить» (вызывает `reload`); `items.length === 0` →
StateBanner empty (пустой список — не ошибка).

## 6. Защита от рассинхрона

1. Единственный источник типов — `src/types/`; компоненты и страницы
   запрещено типизировать ответы API самостоятельно (ESLint-правило из
   документа по сборке).
2. Изменение API-контракта бэкенда = изменение `types/` + `api/endpoints/`
   в одном коммите; композаблы не трогаем — они опираются на типы.
3. Когда бэкенд опубликует OpenAPI — рассмотреть генерацию `types/`
   из спецификации (openapi-typescript) как следующий шаг; в MVP ручные
   интерфейсы достаточны.
4. Поля, которые фронт не использует, в DTO не включаются — меньше
   поверхность рассинхрона (все поля текущих DTO используются в макетах
   ui: `board`/`lot_size`/`full_name`/`isin` нужны автодополнению;
   `fetched_at` — индикатору свежести; `source_url` — модалу деталей;
   `dividend`/`dsi` — блоку метрик C-15 и бейджу C-16).

## 7. Открытые вопросы

Открытых вопросов нет: прежние закрыты решениями ревью раунда 2 —
№1 (порт и base path в dev) — Р-10: порт 8000, base path `/api/v1`,
Vite-proxy `/api` → `http://localhost:8000`; №2 (формат `TickerDetails`)
отменён вместе с эндпоинтом `GET /tickers/{ticker}` решением Р-8.
