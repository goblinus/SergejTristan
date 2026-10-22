export type DividendPeriod = 'year' | 'half_year' | 'quarter';

/** Дивидендные условия одной выплаты. */
export interface DividendTerms {
  period: DividendPeriod | null;
  /** Сумма на одну акцию, ₽. */
  amount_per_share: number | null;
  /** Доходность к последней цене, %; считается на бэкенде. */
  yield_percent: number | null;
}
