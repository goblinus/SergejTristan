import type { WatchStatus } from '@/types/watchlist';

export const DEFAULT_THRESHOLD_DAYS = 7;
export const DEFAULT_SOON_DAYS = 14;

/** Фиксированный порог «неделя» для окраски чипа C-07 (не зависит от threshold_days). */
export const DEADLINE_WEEK_DAYS = 7;

export type DeadlineTone = 'neutral' | 'muted' | 'green' | 'yellow' | 'red';

/**
 * Цвет чипа C-07 определяется числом дней до события, а не серверным `status`.
 * Текст и иконка по-прежнему берутся из `status`.
 */
export function deadlineTone(days: number | null, status: WatchStatus): DeadlineTone {
  if (status === 'past' || (days !== null && days < 0)) {
    return 'muted';
  }
  if (days === null || status === 'no_date') {
    return 'neutral';
  }
  if (days === 0) {
    return 'red';
  }
  if (days <= DEADLINE_WEEK_DAYS) {
    return 'yellow';
  }
  return 'green';
}

/**
 * Локальная оценка зоны для карточек календаря, у которых тикер не в сторожках.
 * Для сторожков источник истины — серверный `status` (Р-3/Р-4).
 */
export function estimateStatus(
  days: number | null,
  thresholdDays: number = DEFAULT_THRESHOLD_DAYS,
  soonDays: number = DEFAULT_SOON_DAYS,
): WatchStatus {
  if (days === null) {
    return 'no_date';
  }
  if (days < 0) {
    return 'past';
  }
  if (days === 0) {
    return 'critical';
  }
  if (days <= thresholdDays) {
    return 'hot';
  }
  if (days <= soonDays) {
    return 'near';
  }
  return 'far';
}
