# Сборка и инструменты фронтенда (MVP)

Дата: 2026-10-19. Статус: **согласован системным дизайнером** — стек фронтенда
принят ADR-0004 ([adr/2026-10-19_adr-0004-стек-фронтенда_system.md](../system/adr/2026-10-19_adr-0004-стек-фронтенда_system.md)),
оформленным по ревью раунда 2 на основании настоящего документа.

Закрываемый вопрос: **единый toolchain до начала разработки** — сборщик,
пакетный менеджер, линтер/форматтер, конфигурация TypeScript, структура
каталогов `frontend/`.

Действующие ADR системной области (`design/system/adr/`):
[ADR-0001 «Выбор СУБД»](../system/adr/2026-10-19_adr-0001-выбор-субд_system.md),
[ADR-0002 «Веб-фреймворк бэкенда»](../system/adr/2026-10-19_adr-0002-веб-фреймворк-бэкенда_system.md),
[ADR-0003 «Стратегия обновления данных»](../system/adr/2026-10-19_adr-0003-стратегия-обновления-данных_system.md),
[ADR-0004 «Стек фронтенда»](../system/adr/2026-10-19_adr-0004-стек-фронтенда_system.md)
(настоящий документ — детализация ADR-0004; ADR — доминирующий документ).

## 1. Решения

| Область | Решение | Обоснование |
|---------|---------|-------------|
| Сборщик | **Vite 5** (`npm create vite`, шаблон `vue-ts`) | Стандарт экосистемы Vue 3, быстрый dev-сервер (ESM), production-бандл на Rollup, proxy к бэкенду из коробки |
| Пакетный менеджер | **npm** (версия в `package.json` → `engines`) | Ноль дополнительной установки для команды из одного-двух разработчиков; lock-файл `package-lock.json` в git |
| Язык | **TypeScript 5**, строгий режим | Типизированная стыковка с API-контрактом (см. 2026-10-19_типы-и-api-клиент_frontend.md) |
| Линтер | **ESLint 9 (flat config)** + `eslint-plugin-vue` (набор `vue3-recommended`) + `@typescript-eslint` | Стандарт для Vue 3 + TS; flat config — актуальный формат |
| Форматтер | **Prettier** | Отделяем форматирование от линтера; ESLint проверяет качество, Prettier — только стиль |
| Роутер | **vue-router 4** | Официальный роутер Vue 3 |
| Тесты | **Vitest** (только для `utils/` и композаблов) | Нативно интегрирован с Vite; в MVP покрываем только логику, не компоненты |
| UI-библиотека | **нет** — чистый CSS + CSS-переменные | См. 2026-10-19_темизация_frontend.md; меньше зависимостей, полный контроль тёмной темы |
| Node.js | **LTS ≥ 20**, версия фиксируется в `.nvmrc` и `engines` | Требование Vite 5 |

Полный список производственных зависимостей MVP: `vue`, `vue-router`.
Dev-зависимости: `vite`, `typescript`, `eslint`, `eslint-plugin-vue`,
`@typescript-eslint/*`, `prettier`, `eslint-config-prettier`, `vitest`,
`@vitejs/plugin-vue`, `vue-tsc`.

## 2. Структура каталогов `frontend/`

```
frontend/
├─ index.html
├─ package.json
├─ package-lock.json
├─ .nvmrc
├─ vite.config.ts
├─ tsconfig.json
├─ tsconfig.node.json          (конфиг для vite.config.ts)
├─ eslint.config.js            (flat config)
├─ .prettierrc.json
├─ env.d.ts                    (/// <reference types="vite/client" />)
├─ public/
│  └─ fonts/                  (Inter, локальные woff2 — см. документ по темизации)
└─ src/
   ├─ main.ts                  (createApp + router)
   ├─ App.vue
   ├─ router/
   │  └─ index.ts              (маршруты, 404)
   ├─ types/                   (DTO и перечисления, слой типов; snake_case,
   │  │                          зеркало API-контракта бэкенда)
   │  ├─ page.ts
   │  ├─ ticker.ts
   │  ├─ meeting.ts
   │  ├─ record-date.ts
   │  └─ watchlist.ts
   ├─ api/
   │  ├─ http.ts               (fetch-обёртка)
   │  ├─ errors.ts             (ApiError)
   │  └─ endpoints/
   │     ├─ tickers.ts
   │     ├─ meetings.ts
   │     ├─ record-dates.ts
   │     └─ watchlist.ts
   ├─ composables/
   │  ├─ useCalendar.ts        (meetings + record-dates, объединённый кэш)
   │  ├─ useWatchlist.ts
   │  ├─ useTickersSearch.ts
   │  ├─ useMeetingDialog.ts   (модал ?meeting=<id>)
   │  ├─ useSnackbar.ts        (очередь уведомлений, undo)
   │  └─ useConnectivity.ts    (офлайн-состояние)
   ├─ components/
   │  ├─ ui/                   (атомы ui-кита C-03..C-14)
   │  ├─ layout/               (AppHeader C-01, BottomNav C-02)
   │  ├─ company/              (CompanyIdentity C-17, CompanyFacts C-15)
   │  ├─ calendar/
   │  └─ watchlist/
   ├─ pages/
   │  ├─ CalendarPage.vue      (route: /calendar; редирект с /)
   │  ├─ WatchlistPage.vue     (route: /me)
   │  └─ NotFoundPage.vue      (catch-all 404; отдельной MeetingPage нет — модал внутри S1)
   ├─ styles/
   │  ├─ tokens.css            (CSS-переменные ui-гайда: --surface-0..4 и др.)
   │  ├─ reset.css
   │  └─ main.css
   └─ utils/
      └─ date.ts
```

## 3. Конфигурация TypeScript

Ключевые флаги `tsconfig.json` (остальное — из шаблона create-vite):

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "exactOptionalPropertyTypes": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "jsx": "preserve",
    "types": ["vite/client"]
  }
}
```

Проверка типов в сборке: `vue-tsc --noEmit` (команда `typecheck`), обязательна
перед коммитом и в CI-шаге, если он появится.

## 4. Скрипты `package.json`

| Скрипт | Назначение |
|--------|-----------|
| `dev` | Vite dev-сервер с proxy на бэкенд |
| `build` | `vue-tsc --noEmit && vite build` |
| `preview` | Просмотр production-сборки |
| `typecheck` | `vue-tsc --noEmit` |
| `lint` | `eslint .` |
| `format` | `prettier --write .` |
| `test` | `vitest run` |

## 5. Proxy к бэкенду и окружения

- Dev: `vite.config.ts` → `server.proxy`: `/api` → `http://localhost:8000`
  (порт бэкенда 8000 по умолчанию и base path `/api/v1` зафиксированы
  решением Р-10 ревью раунда 2; proxy сохраняет путь).
- Base URL бэкенда берётся из `import.meta.env.VITE_API_BASE_URL`,
  значение по умолчанию — `/api`. Файл `.env.local` в git не коммитится;
  шаблон `.env.example` коммитится.

## 6. Правила ESLint, важные для архитектуры

- `vue/multi-word-component-names`: off для `pages/*` (роут-компоненты
  однословные), on для остальных.
- `no-restricted-imports`: запрет импорта `@/api/*` в `src/components/**`
  и `src/pages/**` (доступ к бэкенду — только через композаблы);
  запрет импорта композаблов и api в `src/types/**` и `src/utils/**`.
- Алиас `@` → `src` в `vite.config.ts` и `tsconfig.json` (`paths`).

## 7. Соответствие ADR

Документ детализирует [ADR-0004 «Стек фронтенда»](../system/adr/2026-10-19_adr-0004-стек-фронтенда_system.md)
(статус «Принято»): таблица решений §1, структура каталогов §2, конфигурация
TypeScript §3 и скрипты §4 соответствуют решению ADR. Дополнительные
ограничения настоящего документа (единственные production-зависимости —
`vue`, `vue-router`; date-слой на `Intl.DateTimeFormat` без сторонней
date-библиотеки) зафиксированы в ADR-0004 как сопутствующие решения.
Документ согласован; реализация в `frontend/` может начинаться.
