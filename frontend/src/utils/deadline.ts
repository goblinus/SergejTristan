import type { WatchStatus } from '@/types/watchlist';

export const DEFAULT_THRESHOLD_DAYS = 7;
export const DEFAULT_SOON_DAYS = 14;

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