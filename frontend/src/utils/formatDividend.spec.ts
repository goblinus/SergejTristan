import { describe, expect, it } from 'vitest';

import { formatDsi, formatMoney, formatPercent, formatPeriod } from './formatDividend';
import { formatDate, daysUntil, formatDaysLabel, monthRange, addMonths } from './date';

const NBSP = String.fromCharCode(0xa0);

describe('formatDividend', () => {
  it('форматирует период', () => {
    expect(formatPeriod('year')).toBe('год');
    expect(formatPeriod('half_year')).toBe('полгода');
    expect(formatPeriod('quarter')).toBe('квартал');
    expect(formatPeriod(null)).toBe('—');
  });

  it('форматирует деньги в русской локали', () => {
    expect(formatMoney(33.3)).toBe(`33,30${NBSP}₽`);
    expect(formatMoney(1300)).toBe(`1${NBSP}300,00${NBSP}₽`);
    expect(formatMoney(null)).toBe('—');
  });

  it('форматирует проценты', () => {
    expect(formatPercent(8.4)).toBe('8,4%');
    expect(formatPercent(null)).toBe('—');
  });

  it('форматирует DSI', () => {
    expect(formatDsi(82)).toBe('82');
    expect(formatDsi(null)).toBe('—');
  });
});

describe('date utils', () => {
  it('форматирует дату дд.мм.гггг', () => {
    expect(formatDate('2026-11-09')).toBe('09.11.2026');
  });

  it('считает дни до даты', () => {
    const now = new Date(2026, 9, 20);
    expect(daysUntil('2026-10-20', now)).toBe(0);
    expect(daysUntil('2026-10-23', now)).toBe(3);
    expect(daysUntil('2026-10-19', now)).toBe(-1);
  });

  it('склоняет дни', () => {
    expect(formatDaysLabel(1)).toBe('1 день');
    expect(formatDaysLabel(3)).toBe('3 дня');
    expect(formatDaysLabel(7)).toBe('7 дней');
    expect(formatDaysLabel(21)).toBe('21 день');
  });

  it('считает границы месяца и сдвиг', () => {
    expect(monthRange('2026-02')).toEqual({ from: '2026-02-01', to: '2026-02-28' });
    expect(addMonths('2026-12', 1)).toBe('2027-01');
    expect(addMonths('2026-01', -1)).toBe('2025-12');
  });
});
