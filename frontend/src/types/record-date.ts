export type RecordDateKind = 'dividend_payment' | 'meeting_participation';

/** Дата отсечки (GET /record-dates). */
export interface RecordDate {
  ticker: string;
  /** YYYY-MM-DD. */
  record_date: string;
  kind: RecordDateKind;
  meeting_id: number | null;
  /** ISO 8601 UTC. */
  fetched_at: string;
}

/** Вложенная в Meeting сокращённая отсечка. */
export interface MeetingRecordDate {
  record_date: string;
  kind: RecordDateKind;
  fetched_at?: string;
}

/** Параметры GET /record-dates. */
export type RecordDatesQuery = {
  from?: string;
  to?: string;
  ticker?: string;
  kind?: RecordDateKind;
  page?: number;
  page_size?: number;
};
