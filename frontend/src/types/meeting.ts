import type { DividendTerms } from './dividend';
import type { MeetingRecordDate } from './record-date';

export type MeetingType = 'annual' | 'extraordinary';

/** Собрание акционеров (GET /meetings, GET /meetings/{id}). */
export interface Meeting {
  id: number;
  ticker: string;
  short_name: string;
  logo_url: string | null;
  /** YYYY-MM-DD. */
  meeting_date: string;
  meeting_type: MeetingType;
  description: string | null;
  /** Связанная отсечка dividend_payment; null — ещё не назначена. */
  record_date: MeetingRecordDate | null;
  dividend: DividendTerms | null;
  /** Индекс стабильности дивидендов, 0..100; null — недостаточно истории. */
  dsi: number | null;
  source_url: string | null;
  /** ISO 8601 UTC. */
  fetched_at: string;
}

/** Параметры GET /meetings. */
export type MeetingsQuery = {
  from?: string;
  to?: string;
  ticker?: string;
  page?: number;
  page_size?: number;
};
