# Фронтенд «Дивидендного календаря»

Реализация MVP по спецификациям `design/frontend/` и `design/ui/`; визуальная
основа — прототип `design/makets/`.

## Стек

- Vue 3 (Composition API, `<script setup lang="ts">`), Vue Router 4;
- TypeScript 5 (strict), Vite 5, ESLint 9 (flat config), Prettier, Vitest;
- без UI-библиотек и без Pinia: состояние на композаблах;
- тёмная тема на CSS-токенах из `design/ui/2026-10-19_visual-style_ui.md`;
- шрифт — системный стек с приоритетом Inter; иконки — локальные inline-SVG
  (`src/components/ui/iconPaths.ts`), без CDN.

## Запуск

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Dev-сервер проксирует `/api` и `/static` на бэкенд `http://localhost:8000`.
Базовый URL API задаётся `VITE_API_BASE_URL` (по умолчанию `/api`).

Скрипты: `dev`, `build`, `preview`, `typecheck`, `lint`, `format`, `test`.

## Структура

```
src/
├─ api/            fetch-обёртка, ApiError, endpoints
├─ composables/    useCalendar, useWatchlist, useTickersSearch,
│                  useMeetingDialog, useSnackbar, useConnectivity,
│                  useMediaQuery
├─ components/
│  ├─ ui/          AppIcon, AppButton, TickerChip, DeadlineIndicator,
│  │               Skeleton, SnackbarHost, StateBanner, DropdownList
│  ├─ company/     CompanyIdentity, CompanyFacts
│  ├─ dividend/    DsiBadge, dsiHint
│  ├─ calendar/    MonthFilter, MeetingsGrid, MeetingCard,
│  │               UpcomingList, MeetingDetailsDialog
│  ├─ watchlist/   TickerAutocomplete, StatusFilterChips,
│  │               WatchlistList, WatchRow
│  └─ layout/      AppHeader, BottomNav
├─ pages/          CalendarPage, WatchlistPage, NotFoundPage
├─ router/         маршруты и валидация query
├─ styles/         tokens.css, reset.css, main.css
├─ types/          DTO, зеркало API-контракта (snake_case)
└─ utils/          date.ts, formatDividend.ts, deadline.ts
```

## Проверка совместимости с REST API (2026-10-22)

Проверено против запущенного бэкенда на `127.0.0.1:8000`:

| Проверка | Результат |
|---|---|
| `GET /health` | 200 `{"status":"ok"}` |
| `GET /api/v1/tickers?q=sber&page_size=3` | 200, структура `Page<Ticker>` совпадает |
| `GET /api/v1/meetings?from&to` | 200, все поля DTO совпадают |
| `GET /api/v1/record-dates?from&to&kind` | 200, `Page<RecordDate>` совпадает |
| `GET /api/v1/meetings/{id}` (404) | 404 `{"detail":"meeting not found"}` |
| `from > to` | 422 `{"detail":"from must be <= to"}` |
| Ошибка валидации `page=0` | 422, `detail` — массив `{loc,msg,type}` (обрабатывается) |
| `GET /api/v1/watchlist` | 200, структура совпадает |
| `POST /api/v1/watchlist` | **501 not implemented** |
| `DELETE /api/v1/watchlist/{ticker}` | **501 not implemented** |
| Vite-proxy `/api` | работает |
| Vite-proxy `/static` | работает, но `backend/static/logos/` пуст |

Расхождения и ограничения бэкенда (фронтенд их корректно обрабатывает):

1. `POST`/`DELETE` сторожков — заглушки 501. UI покажет snackbar с ошибкой и
   кнопкой «Повторить» (для 404 — без повтора).
2. `GET /watchlist` пока всегда пуст: `repositories/watchlist.list_items`
   возвращает `[]`; `next_meeting_date` и `next_dividend` — `null` (TODO).
3. Все `logo_url` в БД — `null`; `backend/static/logos/` пуст. UI показывает
   монограмму, как предусмотрено C-17.
4. В БД все `record_dates` имеют `kind = meeting_participation`; календарь
   запрашивает `dividend_payment`, поэтому список отсечек и вложенная
   `record_date` в собраниях пусты — это данные, а не расхождение контракта.
5. `Meeting.source_url` в бэкенде обязателен, во фронтенд-типе допускает
   `null` (совместимо). `MeetingRecordDate.fetched_at` бэкенд отдаёт
   дополнительно — во фронтенд-типе поле необязательное.

## Доступность и поведение

- Состояния каждого асинхронного блока: loading (skeleton) / error / empty / data.
- Статус сторожка не пересчитывается: для S2 используется серверный
  `status` + `days_to_cutoff`; для карточек календаря без сторожка —
  локальная оценка с порогами T=7, S=14.
- «Отменить» после снятия сторожка повторяет `POST` со снимком
  `{ticker, threshold_days}` (сработает после реализации POST в бэкенде).
- Deep-link `?meeting=<id>` восстанавливает модал через `GET /meetings/{id}`;
  `?ticker=<CODE>` на `/me` одноразово префиллит поиск.
