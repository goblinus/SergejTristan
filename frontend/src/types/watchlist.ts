import type { DividendTerms } from './dividend';

/** Каноническая шкала статусов; вычисляется на сервере. */
export type WatchStatus = 'no_date' | 'far' | 'near' | 'hot' | 'critical' | 'past';

/** Фильтр списка сторожков (C-10). */
export type WatchlistFilter = 'all' | 'hot' | 'no_date' | 'past';

/** Сторожок (GET /watchlist). */
export interface WatchlistItem {
  ticker: string;
  short_name: string;
  logo_url: string | null;
  threshold_days: number;
  /** ISO 8601 UTC. */
  created_at: string;
  next_record_date: string | null;
  next_meeting_date: string | null;
  days_to_event: number | null;
  status: WatchStatus;
  next_dividend: DividendTerms | null;
  dsi: number | null;
}

/** Тело POST /watchlist. */
export interface WatchlistCreate {
  ticker: string;
  threshold_days?: number;
}

/** Результат POST /watchlist: created=true для 201. */
export interface AddWatchlistResult {
  item: WatchlistItem;
  created: boolean;
}
