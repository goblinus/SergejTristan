# Архитектура фронтенда «Дивидендный календарь» (MVP)

Дата: 2026-10-19. Статус: проект, раунд 3 (доработка по ревью system-designer
раунда 2; решения Р-4…Р-6, Р-9).

## 1. Цель и охват

Документ фиксирует структуру приложения Vue 3: слои, ответственность модулей,
дерево компонентов экранов S1 (Календарь) и S2 (Мои сторожки) по вайрфреймам
`design/ui/2026-10-19_wireframes_ui.md` и составу UI-кита
`design/ui/2026-10-19_ui-component-kit_ui.md` (C-01..C-14).

Закрываемый вопрос: **как организован код и кто за что отвечает.**

Ограничения MVP: два экрана + модал деталей собрания (S1.1) и мобильная
компоновка (≤640px, в объёме по Р-6). Авторизация, уведомления за пределами
приложения — вне объёма.

Схема: [2026-10-19_components-schema_frontend](./2026-10-19_components-schema_frontend.puml).

## 2. Технологические рамки

- Vue 3, Composition API, однофайловые компоненты с `<script setup lang="ts">`.
- TypeScript в строгом режиме (см. [2026-10-19_building-and-tools_frontend](./2026-10-19_building-and-tools_frontend.md)).
- Vue Router 4 — маршруты `/calendar` (редирект с `/`) и `/me`, модал
  деталей через `?meeting=<id>` (см. [2026-10-19_routing_frontend](./2026-10-19_routing_frontend.md)).
- Состояние — композаблы на базе `reactive`/`ref`, без Pinia (обоснование:
  [2026-10-19_state-management_frontend](./2026-10-19_state-management_frontend.md)).
- Тёмная тема — CSS-переменные по ui-гайду (единственный источник истины —
  `design/ui/2026-10-19_visual-style_ui.md`), без UI-библиотеки
  (см. [2026-10-19_theme_frontend](./2026-10-19_theme_frontend.md)).

## 3. Слои приложения

Направление зависимостей строго сверху вниз; обратные зависимости запрещены.

```
┌─────────────────────────────────────────────┐
│ pages/        Экраны (роут-компоненты)      │
├─────────────────────────────────────────────┤
│ components/   Переиспользуемые компоненты   │
├─────────────────────────────────────────────┤
│ composables/  Композаблы: состояние + логика│
├─────────────────────────────────────────────┤
│ api/          HTTP-клиент + DTO + endpoints │
├─────────────────────────────────────────────┤
│ types/        TypeScript-модель данных      │
└─────────────────────────────────────────────┘
```

### 3.1. `types/` — модель данных

Чистые TypeScript-интерфейсы DTO (`snake_case`, зеркало API-контракта) и
доменные перечисления. Не импортируют ничего из остальных слоёв. Контракты
описаны в [2026-10-19_types-and-api-client_frontend](./2026-10-19_types-and-api-client_frontend.md).

### 3.2. `api/` — доступ к бэкенду

- `http.ts` — обёртка над `fetch`: base URL из env, нормализация ошибок
  в `ApiError` (`{detail}`), таймаут.
- `endpoints/` — один модуль на ресурс: `tickers.ts`, `meetings.ts`,
  `record-dates.ts`, `watchlist.ts`. Функции вида
  `getMeetings(params): Promise<Page<Meeting>>`.
- Никакого состояния в этом слое: только запросы; типы совпадают с JSON
  (мэппинг-кейс отсутствует, Р-1).

### 3.3. `composables/` — состояние и прикладная логика

Композаблы: `useCalendar()`, `useWatchlist()`, `useTickersSearch()`,
`useMeetingDialog()` (состояние модала деталей), `useSnackbar()` (очередь
уведомлений), `useConnectivity()` (офлайн-баннер). Каждый серверный
композабл:
- хранит серверный кэш своего ресурса (на уровне модуля — разделяемое между
  экранами состояние);
- предоставляет `ref`-состояния `data / isLoading / error`;
- инкапсулирует вызовы `api/endpoints` и правила инвалидации.

Компоненты не вызывают `api/` напрямую — только через композаблы.

### 3.4. `components/` — переиспользуемые компоненты

Глупые (presentational) компоненты: вход через props, выход через события.
Не содержат вызовов API и глобального состояния. Подгруппы:
- `components/ui/` — атомы ui-кита: AppButton (C-03), TickerChip (C-05),
  DeadlineIndicator (C-07), Skeleton (C-11), Snackbar (C-12), StateBanner
  (C-13), DropdownList (C-14, внутренний для TickerAutocomplete);
- `components/calendar/` — блоки календаря (MeetingCard, фильтры, UpcomingList);
- `components/watchlist/` — блоки страницы сторожков (TickerAutocomplete,
  WatchRow, StatusFilterChips);
- `components/layout/` — AppHeader (C-01), BottomNav (C-02).

Исключение: контейнерные компоненты уровня фичи (смарт) могут вызывать
композаблы, если это избавляет от чрезмерного prop-drilling. Правило:
композабл вызывается либо в page, либо в одном смарт-контейнере экрана.

Соответствие ui-киту: каждый компонент C-01..C-14 имеет ровно одну
реализацию; визуальные токены — только по ui-гайду.

### 3.5. `pages/` — роут-компоненты

Один файл на маршрут (`CalendarPage`, `WatchlistPage`, `NotFoundPage`).
Ответственность:
- собрать композаблы и компоненты;
- держать локальное состояние экрана (фильтр месяца, свёрнутость
  «Прошедшие», строка поиска);
- ничего не знать об HTTP.

Отдельной страницы собрания нет — `MeetingDetailsDialog` (C-08) живёт
внутри `CalendarPage` и управляется query-параметром `?meeting=<id>`.

## 4. Дерево компонентов

Каркас приложения:

```
App
├─ layout/AppHeader (C-01)          (название, вкладки «Календарь»/«Мои сторожки»,
│  │                                 индикатор «обновлено N назад», кнопка «Обновить»;
│  │                                 бейдж-счётчик hot/critical на вкладке
│  │                                 «Мои сторожки» — Р-9, см. ниже)
│  └─ ui/StateBanner (C-13 offline) (бейдж «нет соединения», состояние офлайн)
├─ RouterView                       (CalendarPage / WatchlistPage / NotFoundPage)
├─ layout/BottomNav (C-02)          (≤640px: «Календарь», «Мои сторожки»;
│                                    бейдж hot/critical на пункте «Мои сторожки» — Р-9)
└─ ui/SnackbarHost (C-12)           (глобальные подтверждения/ошибки, портал)
```

### 4.1. Экран S1 «Календарь» (`/calendar`, компонент `CalendarPage`)

```
CalendarPage
├─ calendar/MonthFilter          (переключатель месяца ◀ ▶; чекбокс «Показать прошедшие»)
│  └─ ui/AppButton (icon)
├─ calendar/MeetingsGrid         (сетка карточек: 3 кол ≥1024px, 2 кол 640–1024px, 1 кол <640px;
│  │                              секции «Предстоящие» и «Прошедшие» — последняя сворачивается)
│  ├─ calendar/MeetingCard (C-06)
│  │  ├─ ui/CompanyIdentity (C-17) (логотип + TickerChip + имя; fallback-монограмма)
│  │  ├─ ui/CompanyFacts (C-15)  (период, сумма на акцию, доходность, собрание, отсечка)
│  │  ├─ ui/DeadlineIndicator (C-07)
│  │  └─ ui/DsiBadge (C-16)      (последним в карточке; подсказка по hover/focus)
│  ├─ ui/Skeleton (C-11, карточка)   (загрузка)
│  └─ ui/StateBanner (C-13, empty/error) (нет собраний в месяце / ошибка загрузки)
├─ calendar/UpcomingList         (ближайшие отсечки под сеткой; включает отсечки
│  │                              без собрания — из GET /record-dates)
│  └─ calendar/UpcomingItem
│     ├─ ui/TickerChip (C-05)
│     └─ ui/DeadlineIndicator (C-07)
├─ calendar/MeetingDetailsDialog (C-08)  (модал S1.1; открыт при ?meeting=<id>;
│  └─ ui/Skeleton (C-11, поля)           на мобильной — bottom-sheet)
└─ ui/Spinner/полоса прогресса под шапкой (loading по C-01)
```

Данные: `useCalendar(month)` → meetings + record-dates (объединённая проекция);
`useWatchlist()` — реактивная подсветка «отслеживается»; `useMeetingDialog()` —
состояние модала по `?meeting=<id>`.

Замечание ревью: месячный грид (CalendarMonth/CalendarDay/EventChip) исключён —
ui-kit его явно не проектирует (см. «Что не входит в UI-kit MVP»); S1 — это
сетка карточек MeetingCard с фильтром месяца.

`MeetingDetailsDialog` (состав по C-08, дивидендные метрики и логотип — ADR-0005/0006):
заголовок (CompanyIdentity: логотип + TickerChip + эмитент), дата собрания, дата
отсечки (или «будет объявлена позже»), повестка, период выплат, сумма на акцию,
доходность, блок статуса сторожка с CTA «Отслеживать этот тикер»/«Сторожок
установлен», ссылка на источник (`source_url`; при `source_url === null` строка
скрывается), DSI последней строкой, кнопка закрытия.

### 4.2. Экран S2 «Мои сторожки» (`/me`, компонент `WatchlistPage`)

```
WatchlistPage
├─ watchlist/TickerAutocomplete (C-04)      (поле поиска + dropdown-подсказки;
│  ├─ ui/DropdownList (C-14, внутренний)     префилл из ?ticker=, автофокус,
│  │  └─ ui/AppButton («Отслеживать»/        дебаунс 300 мс, мин. 2 символа;
│  │       disabled «Уже отслеживается»)     no-results/error-состояния)
├─ watchlist/StatusFilterChips (C-10)       («все», «горячие» (hot/critical),
│                                            «без даты», «прошла»)
├─ watchlist/WatchlistList
│  ├─ watchlist/WatchRow (C-09)
│  │  ├─ ui/CompanyIdentity (C-17) (логотип + TickerChip + имя); ui/AppButton (icon, delete)
│  │  ├─ ui/CompanyFacts (C-15)  (период, сумма, доходность, собрание, отсечка)
│  │  ├─ ui/DeadlineIndicator (C-07)  (status и days_to_event из API; цвет — по дням)
│  │  └─ ui/DsiBadge (C-16)      (последним в нижней строке)
│  ├─ ui/Skeleton (C-11, строка)      (загрузка)
│  └─ ui/StateBanner (C-13, empty/error) (пустой список: CTA «Найти тикер»)
└─ (модалов нет)
```

Данные: `useWatchlist()` (список + мутации add/remove),
`useTickersSearch(query)` (справочник MOEX, debounce 300 мс),
`useSnackbar()` (подтверждения «Сторожок установлен/снят» + undo).

### 4.3. Snackbar с undo (C-12)

`SnackbarHost` — глобальный портал в каркасе, очередь — в `useSnackbar()`.
Подтверждение снятия сторожка показывает action «Отменить» в течение окна
5 сек: undo = повторный `POST /watchlist` с телом `{ ticker, threshold_days }`
из снимка, сделанного перед удалением (прежний порог восстанавливается —
см. [2026-10-19_state-management_frontend](./2026-10-19_state-management_frontend.md), §4) — укладывается
в идемпотентную семантику API (200/201, POST не создаёт дубль). DELETE выполняется
сразу (без отложенной отправки), откат — новым POST. Ошибки мутаций —
Snackbar error с действием «Повторить».

### 4.4. Глобальные состояния

- **Офлайн**: `useConnectivity()` (события `online`/`offline` + ошибки
  `kind: 'network'`) → StateBanner offline под шапкой; интерактивные
  действия блокируются, данные показываются с баннером «данные могли
  устареть».
- **Свежесть данных**: индикатор «обновлено N назад» в AppHeader строится по
  минимальному `fetched_at` показанных записей (meetings + record-dates на
  S1, watchlist — без `fetched_at`, поэтому берётся из данных календаря);
  helper `utils/date.ts:formatFreshness()`. При отсутствии `fetched_at`
  метка скрывается (ui-гайд, §6 индикации сроков).
- **Кнопка «Обновить»** в AppHeader вызывает `reload()` композабла активного
  экрана.
- **Бейдж-счётчик «горячих» сторожков (Р-9, в объёме MVP)**: на вкладке
  «Мои сторожки» в AppHeader (C-01) и на одноимённом пункте BottomNav (C-02)
  отображается число сторожков со статусом `hot`/`critical`. Реализация —
  `computed` по `useWatchlist().items` (отдельных запросов нет); бейдж скрыт,
  когда счётчик равен 0 или список ещё не загружен (`items === null`).
  Оформление — нейтральная плашка по токену `--warn-container` ui-гайда,
  без цветовой семантики зон.

## 5. Потоки данных

1. **Загрузка календаря:** `CalendarPage` → `useCalendar(month)` →
   параллельно `api/endpoints/meetings.getMeetings(from, to)` и
   `api/endpoints/record-dates.getRecordDates(from, to, kind='dividend_payment')`
   → объединённый кэш композабла → проекции `cards` / `upcoming` (computed) →
   компоненты. Отсечки без связанного собрания (`meeting_id IS NULL`) попадают
   в UpcomingList и в счётчик найденного (замечание frontend-6, Р-6).
2. **Модал деталей:** клик по MeetingCard → `router.replace` с
   `?meeting=<id>` → `useMeetingDialog` берёт собрание из кэша `useCalendar`;
   если кэша нет (deep-link после перезагрузки) — `GET /meetings/{id}` (Р-6).
3. **Постановка/снятие сторожка:** клик «Отслеживать»/«Снять» →
   `useWatchlist().add(ticker)` / `.remove(ticker)` → `POST`/`DELETE`
   `/api/v1/watchlist` → локальное обновление кэша по ответу → Snackbar
   (успех; для снятия — с «Отменить») → подсветка на S1 обновляется
   реактивно через `watchedTickers` (computed), без перезагрузки календаря.
4. **Ошибки:** `api/http.ts` нормализует ошибки в `ApiError`; композаблы
   выставляют `error`; экраны показывают StateBanner error с «Повторить»;
   ошибки мутаций — Snackbar error.

## 6. Адаптивность (в объёме MVP, Р-6)

- Брейкпоинты ui-гайда: ≥1024px десктоп (3 колонки), 640–1024px планшет
  (2 колонки), ≤640px мобильная компоновка (1 колонка, BottomNav вместо
  вкладок AppHeader, MeetingDetailsDialog — bottom-sheet, поля 16px).
- Реализация — CSS (media query на контейнерах сетки) + composable
  `useMediaQuery('(max-width: 640px)')` для переключения навигации
  (AppHeader-вкладки ↔ BottomNav) и вида модала.

## 7. Правила и ограничения

- Импорт между слоями — только вниз; `pages` и `components` не импортируют
  `api/` (ESLint-правило `no-restricted-imports` — см. документ по сборке).
- Общие типы — только через `types/`; запрещено дублировать DTO в компонентах.
- Форматирование дат — через единый helper `utils/date.ts`
  (`Intl.DateTimeFormat`, формат `dd.MM.yyyy`; `formatFreshness(fetched_at)`
  для «обновлено N назад»); `Date.now()` в шаблонах запрещён.
- Статус сторожка фронтенд не вычисляет: `DeadlineIndicator` получает
  готовую пару `{ status, days_to_event }`. `days_to_event` — дней от
  текущей даты сервера до даты события сторожка: отсечки `dividend_payment`,
  а при её отсутствии — даты собрания с вопросом о дивидендах (решение
  владельца от 2026-10-22, см. `types-and-api-client`, §1.5). Роли полей
  разделены: `status` → текст и иконка, `days_to_event` → цвет чипа
  (решение владельца от 2026-10-22). Тон вычисляет
  `utils/deadline.ts:deadlineTone(days, status)` по трёхцветной шкале:
  `0` → danger, `1..7` → warn, `> 7` → success, `past` → muted,
  `no_date` → neutral; порог недели — константа `DEADLINE_WEEK_DAYS = 7`
  (не `threshold_days`), см.
  [2026-10-19_theme_frontend](./2026-10-19_theme_frontend.md), §6.1.
- Карточки календаря без сторожка: дни считаются локально, зона
  (текст/иконка) — локальная оценка с порогами T=7, граница 14, по §4
  документа ui «индикация-сроков»; цвет берётся из той же шкалы
  `deadlineTone()` по локально посчитанным дням, отдельной палитры у
  локальной оценки нет.
- Каждый асинхронный блок UI обязан иметь четыре состояния: loading
  (Skeleton) / error (StateBanner) / empty (StateBanner empty) / data.

## 8. Открытые вопросы

Открытых вопросов нет: прежний вопрос №1 (бейдж-счётчик сторожков в
hot/critical на вкладке «Мои сторожки») закрыт решением Р-9 — бейдж принят
в объём MVP, реализация описана в §4.4.
