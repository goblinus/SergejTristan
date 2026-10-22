# Темизация: тёмная Material-тема (MVP)

Дата: 2026-10-19. Статус: проект, раунд 2 (доработка по ревью system-designer,
замечание frontend-5; решения Р-4, Р-6). Обновлено 2026-10-22: цвет чипа
`DeadlineIndicator` (C-07) определяется числом дней до события, не `status`
(решение владельца; tokens §2, утилита §6.1).

Закрываемый вопрос: **как визуальные токены попадают в код компонентов** —
CSS-переменные из ui-гайда, базовый reset, решение по UI-библиотеке.

**Единственный источник истины по визуальным токенам —
`design/ui/2026-10-19_visual-style_ui.md`.** Имена переменных, значения,
шрифт и иконки ниже перенесены оттуда без переименовывания. Прежний набор
`--color-*` (Material baseline, Roboto) отменён; отказ от Vuetify подтверждён
системным дизайнером (ревью раунда 1).

## 1. Решение по UI-библиотеке

**Чистый CSS + CSS-переменные, без Vuetify и аналогов** (подтверждено
system-designer).

Обоснование:
- в MVP два экрана и ~15 компонентов, преимущественно текстовые — окупаемость
  библиотеки низкая;
- тёмная тема «из коробки» у Vuetify всё равно требует переопределения
  палитры, а её объём (~300 КБ) непропорционален задаче;
- собственные атомы (`components/ui/`, соответствует ui-киту C-01..C-14)
  полностью контролируют токены и поведение; Material-выразительность
  достаточна на уровне цвета/типографики/скруглений/отступов.

Критерий пересмотра: появление сложных контролов (data-tables c сортировкой,
date-picker) — тогда пересмотр библиотеки через system-designer, токены
переносятся посимвольно.

## 2. Дизайн-токены (`src/styles/tokens.css`)

Именование и значения — ровно по §1 ui-гайда «визуальный-стиль».
Поверхности различаются тоном (`surface-0..4`), без overlay-элевации.
Исключение: `--success-container` введён решением владельца от 2026-10-22
(зелёный чип C-07) и перенесён в ui-гайд 2026-10-22.

```css
:root {
  /* Поверхности и фон */
  --bg-base:          #121214;  /* фон приложения */
  --surface-0:        #161618;  /* scaffold/фоны секций */
  --surface-1:        #1D1D20;  /* AppBar, карточки уровня 1, bottom-nav */
  --surface-2:        #232327;  /* карточки собраний, строки списков */
  --surface-3:        #2B2B30;  /* modal, dropdown, snackbar */
  --surface-4:        #313137;  /* hover поверх surface-3, bottom-sheet */
  --outline:          #3A3A40;  /* границы */
  --outline-variant:  #2A2A2E;  /* разделители */

  /* Текст */
  --on-surface:          #E6E1E8;  /* основной текст */
  --on-surface-variant:  #C9C5CF;  /* вторичный (подписи, метки) */
  --on-surface-muted:    #8E8B96;  /* прошедшее, disabled-текст */

  /* Акценты */
  --primary:              #9DB8FF;  /* активная вкладка, ссылки, primary-кнопки */
  --on-primary:           #0B1026;
  --primary-container:    #2A3454;  /* фон selected/tonal-элементов */
  --on-primary-container: #C6D4FF;

  /* Семантика сроков и статусов (ui «индикация-сроков»; тон чипа — по числу
     дней, решение владельца от 2026-10-22, см. §6.1) */
  --warn:             #FFD54F;  /* чип 1..7 дней до события */
  --on-warn:          #3A2E00;
  --warn-container:   #4A3C12;  /* фон чипа 1..7 дней */
  --danger:           #FF8A80;  /* чип 0 дней («сегодня!») + ошибки */
  --danger-container: #5C1F1B;  /* фон чипа 0 дней */
  --success:          #7FD9A6;  /* > 7 дней до события; подтверждения */
  --success-container: #1F3D2E; /* фон чипа > 7 дней (решение 2026-10-22) */
  --neutral-chip:     #3A3A40;  /* «нет даты» (days = null) */
  --past:             #57575E;  /* «прошла»: приглушённые элементы */

  /* Типографика — Inter с системным фолбэком (ui-гайд, §2) */
  --font-family: "Inter", -apple-system, "Segoe UI", Roboto, sans-serif;

  /* Радиусы и сетка (ui-гайд, §3; шаг 4px) */
  --radius-card:   16px;  /* карточка, модал */
  --radius-chip:   999px; /* pill — чипы статусов (допускается 8px) */
  --radius-field:  12px;  /* текстовое поле (filled) */
  --radius-button: 20px;  /* pill */
  --radius-snack:   8px;
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px;  --space-4: 16px;
  --space-5: 20px; --space-6: 24px; --space-8: 32px;

  /* Тени (ui-гайд, §4 — только modal/dropdown/snackbar) */
  --shadow-modal: 0 8px 24px rgba(0, 0, 0, 0.45);

  /* Z-индексы */
  --z-header: 100;
  --z-modal: 200;
  --z-snackbar: 300;
}
```

Правила:
- Библиотечные hex-коды и «магические» px в компонентах запрещены: стили
  компонентов ссылаются только на токены (`var(--surface-2)`).
- Светлой темы в MVP нет; структура токенов одноуровневая — смена темы позже
  сводится к ещё одному блоку значений.
- Семантика срока кодируется только токенами `--danger*`, `--warn*`,
  `--success*`, `--neutral-chip`, `--past` и парой `--surface-1` +
  `--outline-variant`. Цвет чипа `DeadlineIndicator` (C-07) определяется
  **числом дней до события**, а не серверным `status` (решение владельца от
  2026-10-22): `0` → `--danger-container`/`--danger`, `1..7` →
  `--warn-container`/`--warn`, `> 7` → `--success-container`/`--success`,
  `no_date` (`days = null`) → `--neutral-chip`/`--on-surface-variant`,
  `past` → `--surface-1` с границей `--outline-variant`/
  `--on-surface-muted`. `status` задаёт только текст и иконку (таблица §3
  документа ui «индикация-сроков»). Порог недели — фиксированная константа
  фронтенда `DEADLINE_WEEK_DAYS = 7` (§6.1), а не персональный
  `threshold_days` сторожка. Красный (`--danger`) — только «сегодня!» и
  ошибки, не «прошла».

## 3. Типографика

Шрифт — **Inter** (Open Font License), фолбэк системный
(`-apple-system, "Segoe UI", Roboto, sans-serif`). Подключение: локальные
woff2 (woff2-файлы в `public/fonts/`, `@font-face` в `tokens.css`,
`font-display: swap`) — чтобы исключить скачки раскладки и зависимость от CDN.

Шкала стилей — по ui-гайду §2 (headline-sm 24/32/600 … label-md 12/16/500);
в CSS — utility-классы `.t-body-md` и т.п. либо переменные
`--font-size-body-md: 0.875rem; --line-height-body-md: 1.25rem;`.

Цифры в датах и счётчиках дней — табличные:
`font-feature-settings: "tnum"` (в `DeadlineIndicator`, датах карточек,
строках сторожков), чтобы не прыгала ширина.

Моноширинный шрифт не используется.

## 4. Иконки

Набор — **Material Symbols (Rounded)** (ui-гайд, §6). Подключение —
Google Fonts stylesheet для `Material+Symbols+Rounded` либо локальный
self-hosted вариант; в коде — текстовые лигатуры (`calendar_month`,
`warning`, `delete`, …) внутри компонента-обёртки `ui/AppIcon`
(единая точка для `font-variation-settings`, размера 20/24px и
`aria-hidden`). Размеры: 20px в кнопках/чипах, 24px в AppBar/навигации.

## 5. Базовый reset (`src/styles/reset.css`)

Минимальный современный reset (вместо normalize.css):

- `*, *::before, *::after { box-sizing: border-box; }`
- обнуление margin у заголовков/параграфов/списков;
- `body { margin: 0; font-family: var(--font-family); background:
  var(--bg-base); color: var(--on-surface); }`
- `img { max-width: 100%; display: block; }`,
  `button { font: inherit; color: inherit; }`,
  `input { font: inherit; }`;
- `:root { color-scheme: dark; }` — чтобы нативные контролы (скроллбары,
  input) рендерились тёмными.

## 6. Попадание токенов в компоненты

1. `main.css` импортирует `reset.css` и `tokens.css`; подключается один раз
   в `main.ts`.
2. Стили компонентов — только `<style scoped>` внутри SFC; глобальные стили
   вне `styles/` запрещены.
3. Атомы `components/ui/` (AppButton C-03, TickerChip C-05,
   DeadlineIndicator C-07, Skeleton C-11, Snackbar C-12, StateBanner C-13) —
   единственное место, где реализованы паттерны. Компоненты фич
   (`calendar/`, `watchlist/`) собирают атомы и не переопределяют
   цвета/радиусы напрямую.
4. Вариативность — через props-модификаторы атомов
   (`<AppButton variant="filled|tonal|text|icon">`,
   `<DeadlineIndicator :status="..." :days="...">` — `status` задаёт текст
   и иконку, `days` — цвет чипа; тон вычисляется внутри атома функцией
   `deadlineTone()` из `src/utils/deadline.ts` (§6.1) и маппится на класс
   `is-danger|is-warn|is-success|is-neutral|is-muted`), которые внутри атома
   ссылаются только на токены. Никаких inline-`style` извне.
5. Состояния интерактива (hover/focus/pressed/selected/disabled, state
   layers `--on-surface` 8%/12%) — по §5 ui-гайда, реализуются в атомах
   как служебные классы, в фичах не дублируются.
6. Размеры в rem (кроме 1px-линий); сетка отступов кратна `--space-*`.
   Контентная колонка: `max-width: 1200px`, поля 24px (десктоп) / 16px
   (мобайл) — токен `--space-6`/`--space-4`.

### 6.1. Утилита тона срока (`src/utils/deadline.ts`)

Тон чипа C-07 вычисляется на клиенте **по числу дней**; в выборе цвета
серверный `status` не участвует (цвет — только по дням, решение владельца от
2026-10-22). `status` по-прежнему задаёт текст и иконку чипа.

```ts
import type { WatchStatus } from '@/types/watchlist';

/** Порог «неделя»: константа фронтенда, а не персональный threshold_days */
export const DEADLINE_WEEK_DAYS = 7;

export type DeadlineTone = 'danger' | 'warn' | 'success' | 'neutral' | 'muted';

/** Тон чипа C-07 по числу дней; status различает только past/no_date */
export function deadlineTone(days: number | null, status: WatchStatus): DeadlineTone {
  if (days === null) return status === 'past' ? 'muted' : 'neutral';
  if (days < 0) return 'muted';
  if (days === 0) return 'danger';
  return days <= DEADLINE_WEEK_DAYS ? 'warn' : 'success';
}
```

| `days` | Тон | Класс атома | Фон / текст, иконка | Типичный `status` |
|---|---|---|---|---|
| `0` | danger | `is-danger` | `--danger-container` / `--danger` | `critical` |
| `1..7` | warn | `is-warn` | `--warn-container` / `--warn` | `hot` при T ≥ 7 |
| `> 7` | success | `is-success` | `--success-container` / `--success` | `far`, `near`, `hot` при T > 7 |
| `null` | neutral | `is-neutral` | `--neutral-chip` / `--on-surface-variant` | `no_date` |
| `null` / `< 0` | muted | `is-muted` | `--surface-1` + граница `--outline-variant` / `--on-surface-muted` | `past` |

Следствия, которые нужно учитывать:
- цветовая шкала не совпадает со шкалой зон Р-4: при персональном пороге
  `T > 7` сторожок со `status = hot` и `days = 8..T` получает зелёный чип с
  текстом «осталось N дн.» — текст и цвет отвечают на разные вопросы;
- `far` и `near` (> 7 дней) визуально не различаются — оба зелёные;
- утилита принимает уже вычисленные дни (серверный `days_to_event` либо
  локальная оценка для карточки календаря без сторожка) и статус не считает.

## 7. Доступность (минимум MVP)

- Контраст текста к фону ≥ 4.5:1 (пары токенов ui-гайда дают ≥ 7:1;
  `--on-surface-muted` — только для крупных/декоративных элементов).
- Фокус: видимое кольцо `2px var(--primary)` со смещением 2px у всех
  интерактивных элементов (`:focus-visible` в reset).
- Статус срока воспроизводится текстом и иконкой, не только цветом
  (обязательный текст в `DeadlineIndicator`); цвет по дням (§6.1) —
  дополнительный сигнал, а не единственный носитель смысла.
- `aria-live="polite"` на Snackbar и зонах загрузки/ошибки.
- Клавиатура: стрелки по карточкам/строкам, Enter — открыть/применить,
  Esc — закрыть модал/dropdown.

## 8. Согласование с ui-гайдом

1. Изменение визуального стиля = сначала правка ui-гайда, затем перенос
   значений в `tokens.css` (имена и значения не разносятся).
2. Любой стиль макета, не выразимый текущими токенами, сначала попадает в
   `tokens.css`, затем используется в компоненте — промежуточных констант
   в компонентах не заводим.
3. Расхождение «в макете не тот цвет» — это баг уровня токена, не компонента.

## 9. Открытые вопросы

1. Вопрос закрыт: трёхцветная шкала по дням и токен
   `--success-container: #1F3D2E` синхронизированы с ui-гайдом 2026-10-22
   (`design/ui/2026-10-19_visual-style_ui.md` §1 — токен и правило цвета;
   `design/ui/2026-10-19_dates-indicators_ui.md` §3–§4 — цвет по числу дней;
   C-07 в `design/ui/2026-10-19_ui-component-kit_ui.md`). Расхождений с §2 и
   §6.1 настоящего документа нет.
2. Прочие вопросы закрыты: палитра, типографика, иконки и отказ от Vuetify
   зафиксированы ui-гайдом и подтверждены system-designer.
