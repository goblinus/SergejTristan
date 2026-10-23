# Карточка компании: логотип и строка фактов (frontend)

Дата: 2026-10-20
Область: frontend
Статус: проект, к согласованию system-designer (ADR-0005, ADR-0006)

Назначение: контракты компонентов, форматирование и правила отображения логотипа, периода выплат, суммы на акцию, доходности, даты собрания и даты отсечки в карточках S1/S2 и модале S1.1.

Основание: [2026-10-20_adr-0005-dividend-metrics_system](../system/adr/2026-10-20_adr-0005-dividend-metrics_system.md), [2026-10-20_adr-0006-company-logos_system](../system/adr/2026-10-20_adr-0006-company-logos_system.md), [2026-10-20_dividend-metrics_ui](../ui/2026-10-20_dividend-metrics_ui.md), [2026-10-19_types-and-api-client_frontend](./2026-10-19_types-and-api-client_frontend.md).

## 1. Типы props

```ts
interface CompanyIdentityProps {
  logoUrl: string | null;
  ticker: string;
  name: string;
}

interface CompanyFactsProps {
  period: DividendPeriod | null;
  amountPerShare: number | null;
  yieldPercent: number | null;
  meetingDate: string | null;   // YYYY-MM-DD
  cutoffDate: string | null;    // YYYY-MM-DD
}

interface DsiBadgeProps {
  value: number | null;
}
```

Компоненты не объявляют собственные интерфейсы API-полей — только props.

## 2. Компоненты

### 2.1. `CompanyIdentity` (`src/components/company/CompanyIdentity.vue`)

- Состав: логотип 32×32, тикер, название эмитента.
- `logoUrl` — относительный путь или https-URL из API.
- Если `logoUrl === null` или картинка не загрузилась — монограмма: первая буква тикера на `--surface-3`, 32×32, радиус 8.
- Логотип декоративный: `alt=""`, рядом всегда есть название; клика по нему нет.
- В модале S1.1 — тот же компонент с размером 36×36 (через prop `size`).

```vue
<img v-if="logoUrl && !failed" :src="logoUrl" alt="" width="32" height="32" @error="failed = true">
<span v-else class="company__monogram" aria-hidden="true">{{ ticker[0] }}</span>
```

### 2.2. `CompanyFacts` (`src/components/company/CompanyFacts.vue`)

- Рендерит `dl` из пяти ячеек в одну строку:
  - «Период» — `год` / `полгода` / `квартал`;
  - «На акцию» — `33,30 ₽`;
  - «Доходность» — `8,4%`;
  - «Собрание» — `12.11.2026`;
  - «Отсечка» — `09.11.2026`.
- Только отображение: доходность и DSI не пересчитываются.
- `null` в метриках и датах → `—`; строка фактов не скрывается.
- Доступность: нативная семантика `dl/dt/dd`; значения читаются после подписей.
- Классы: `facts` (grid 5 колонок), значения — `tabular-nums`.
- На мобильной ширине — те же 5 колонок с уменьшенным кеглем (10/11.5 px); перенос дат на вторую строку не допускается.

### 2.3. `DsiBadge` (`src/components/dividend/DsiBadge.vue`)

- Состав: `DSI`, значение (целое 0–100), кнопка-иконка `i`.
- `value: null` → `DSI —`, иконка остаётся активной.
- Подсказка — CSS-only (hover + `:focus`), без порталов и JS-позиционирования:
  пузырь абсолютно позиционирован над иконкой, `pointer-events: none`.
- Клик/Enter/Space по иконке **не** должны всплывать до карточки/строки: в
  `MeetingCard`/`WatchRow` обработчик открытия деталей обязан игнорировать
  `event.target.closest('.dsi__hint')`.
- Текст подсказки — константа `DSI_HINT` из `src/components/dividend/dsiHint.ts`;
  `aria-label` кнопки = `DSI_HINT`, визуальный пузырь `aria-hidden="true"`.
- Значение не окрашивается по уровню (в MVP нейтрально).

Текст `DSI_HINT`:

> DSI — индекс стабильности дивидендов, 0–100. Учитывает регулярность и изменчивость выплат за последние 5 лет: чем выше, тем стабильнее дивидендный поток. 80+ — высокая стабильность, 50–79 — средняя, ниже 50 — низкая.

## 3. Форматирование (`src/utils/formatDividend.ts`)

```ts
export const PERIOD_LABELS: Record<DividendPeriod, string> = {
  year: 'год',
  half_year: 'полгода',
  quarter: 'квартал'
};

export function formatPeriod(period: DividendPeriod | null): string;   // «год» | «—»
export function formatMoney(value: number | null): string;             // «1 300,00 ₽» | «—»
export function formatPercent(value: number | null): string;           // «8,4%» | «—»
export function formatDsi(value: number | null): string;               // «82» | «—»
export function formatDate(isoDate: string): string;                   // «12.11.2026»
```

Правила:

- `formatMoney` — `Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })`, неразрывный пробел перед `₽`.
- `formatPercent` — один знак после запятой, `%` без пробела.
- `formatDsi` — целое, без знака `%`; значения вне 0–100 не приходят.
- `formatDate` — `YYYY-MM-DD` → `dd.mm.yyyy`, без времени и зоны.
- Функции чистые, покрываются unit-тестами.

## 4. Размещение

| Место | Порядок |
|---|---|
| `MeetingCard` (C-06) | `CompanyIdentity` (+★) → `CompanyFacts` → `DeadlineIndicator` + `DsiBadge` (DSI последним) |
| `WatchRow` (C-09) | `CompanyIdentity` + «Снять» → `CompanyFacts` → `DeadlineIndicator` + `DsiBadge` (DSI последним) |
| `MeetingDetailsDialog` (C-08) | `CompanyIdentity` в заголовке; строки дат и метрик; `DsiBadge` — последняя строка после «Источник» |

В `WatchRow` строка фактов ограничена по ширине (`max-width: 720px`), чтобы
на десктопе пять колонок не растягивались на всю ширину списка.

## 5. Маппинг API → props

- `MeetingCard`:
  - `CompanyIdentity`: `meeting.logo_url`, `meeting.ticker`, `meeting.short_name`;
  - `CompanyFacts`: `meeting.dividend.period`, `.amount_per_share`, `.yield_percent`, `meeting.meeting_date`, `meeting.record_date?.record_date` (или `—`, если отсечки нет);
  - `DsiBadge`: `meeting.dsi`.
- `WatchRow`:
  - `CompanyIdentity`: `item.logo_url`, `item.ticker`, `item.short_name`;
  - `CompanyFacts`: «Период»/«На акцию»/«Доходность» — из
    `item.next_dividend` (`.period`, `.amount_per_share`, `.yield_percent`),
    «Собрание» — `item.next_meeting_date`, «Отсечка» — `item.next_record_date`;
  - `DsiBadge`: `item.dsi`.
- `MeetingDetailsDialog`: `meeting.logo_url`, `meeting.dividend`, `meeting.dsi`.

Поля `next_*` — результат выбора события на бэкенде (решение владельца от
2026-10-22): `next_record_date` содержит дату события, а не обязательно дату
закрытия реестра. При отсутствии будущей отсечки подставляется дата собрания
с вопросом о дивидендах, и `next_record_date === next_meeting_date`; условия
выплаты в `next_dividend` берутся из этого собрания. Признака источника в DTO
нет, поэтому строка S2 отображает поля как есть, без выбора между «отсечкой» и
«собранием».

Никаких вычислений `yield = dps / price` на клиенте: цена и доходность — зона
бэкенда. Это же правило действует для DSI (готовый снапшот).

## 6. Состояния и края

- Загрузка — скелетон карточки/строки с логотипом-заглушкой и полосой фактов.
- Прошедшее собрание — факты видны; общее приглушение по C-06/C-09.
- Частичные данные: `period` известен, `amount_per_share` — нет → «—» только в сумме; пять колонок сохраняются.
- Нет отсечки (`record_date === null` в `Meeting`; `next_record_date === null`
  в `WatchlistItem` — будущих событий нет) → в ячейке «Отсечка» `—`,
  карточка/строка не скрывается.
- Нет логотипа → монограмма; интерфейс не «прыгает» (фиксированные 32×32).
- DSI `null`: бейдж `DSI —`, подсказка доступна.

## 7. Тесты

- Unit: `formatMoney`, `formatPercent`, `formatPeriod`, `formatDsi`, `formatDate`, `null`.
- Component: `CompanyIdentity` с URL, `null` и ошибкой загрузки; `CompanyFacts` с полными/частичными данными; `DsiBadge` с `null` и числом.
- Interaction: hover/focus показывает подсказку; клик по иконке не открывает модал; Esc/уход фокуса скрывает.
- E2E: S1 и S2 содержат логотип, пять фактов и DSI последним; модал содержит логотип и факты.

## 8. Границы

- Нет графика/истории выплат и сравнения с сектором.
- Нет редактирования метрик.
- Нет цветовой шкалы DSI.
- Нет клиентского пересчёта доходности/DSI.
- Нет хотлинка логотипов с сайтов эмитентов: только `logo_url` из API.

## 9. Связанные документы

- [2026-10-19_types-and-api-client_frontend](./2026-10-19_types-and-api-client_frontend.md)
- [2026-10-19_frontend-architecture_frontend](./2026-10-19_frontend-architecture_frontend.md)
- [2026-10-20_dividend-metrics_ui](../ui/2026-10-20_dividend-metrics_ui.md)
- [2026-10-19_api-contract_backend](../backend/2026-10-19_api-contract_backend.md)
- [2026-10-20_adr-0006-company-logos_system](../system/adr/2026-10-20_adr-0006-company-logos_system.md)
