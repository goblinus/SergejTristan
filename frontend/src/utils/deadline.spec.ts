import { describe, expect, it } from 'vitest';

import { DEADLINE_WEEK_DAYS, deadlineTone } from './deadline';

describe('deadlineTone', () => {
  it('фиксирует недельный порог', () => {
    expect(DEADLINE_WEEK_DAYS).toBe(7);
  });

  it('нейтральный тон при отсутствии даты', () => {
    expect(deadlineTone(null, 'no_date')).toBe('neutral');
    expect(deadlineTone(null, 'far')).toBe('neutral');
  });

  it('приглушённый тон для прошедших дат', () => {
    expect(deadlineTone(-1, 'past')).toBe('muted');
    expect(deadlineTone(-1, 'far')).toBe('muted');
    expect(deadlineTone(-30, 'past')).toBe('muted');
  });

  it('красный тон в день события', () => {
    expect(deadlineTone(0, 'critical')).toBe('red');
    expect(deadlineTone(0, 'hot')).toBe('red');
  });

  it('жёлтый тон на границе недели', () => {
    expect(deadlineTone(1, 'hot')).toBe('yellow');
    expect(deadlineTone(7, 'near')).toBe('yellow');
  });

  it('зелёный тон дальше недели', () => {
    expect(deadlineTone(8, 'near')).toBe('green');
    expect(deadlineTone(30, 'far')).toBe('green');
  });

  it('серверный status=past важнее положительного числа дней', () => {
    expect(deadlineTone(0, 'past')).toBe('muted');
    expect(deadlineTone(3, 'past')).toBe('muted');
  });
});
