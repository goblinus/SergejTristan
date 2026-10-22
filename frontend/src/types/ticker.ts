/** Ценная бумага MOEX (GET /tickers). */
export interface Ticker {
  /** Торговый код (SECID), верхний регистр. */
  ticker: string;
  short_name: string;
  full_name: string | null;
  isin: string | null;
  board: string | null;
  lot_size: number | null;
  /** Относительный путь или https-URL логотипа; null — показываем монограмму. */
  logo_url: string | null;
  is_active: boolean;
  /** ISO 8601 UTC. */
  fetched_at: string;
}

/** Параметры GET /tickers. */
export type TickersQuery = {
  q?: string;
  page?: number;
  page_size?: number;
};
