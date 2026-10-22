import type { DividendPeriod } from '@/types/dividend';

export const PERIOD_LABELS: Record<DividendPeriod, string> = {
  year: 'год',
  half_year: 'полгода',
  quarter: 'квартал',
};

const DASH = '—';
const NBSP = String.fromCharCode(0xa0);

/** Период выплат: «год» / «полгода» / «квартал» / «—». */
export function formatPeriod(period: DividendPeriod | null | undefined): string {
  return period ? PERIOD_LABELS[period] : DASH;
}

/** Сумма на акцию: «1 300,00 ₽» или «—». */
export function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return DASH;
  }
  const formatted = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
  return `${formatted}${NBSP}₽`;
}

/** Доходность: «8,4%» или «—». */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return DASH;
  }
  const formatted = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
  return `${formatted}%`;
}

/** DSI: целое 0..100 без знака «%», либо «—». */
export function formatDsi(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return DASH;
  }
  return String(Math.round(value));
}
