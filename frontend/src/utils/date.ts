const MONTH_NAMES = [
  'Январь',
  'Февраль',
  'Март',
  'Апрель',
  'Май',
  'Июнь',
  'Июль',
  'Август',
  'Сентябрь',
  'Октябрь',
  'Ноябрь',
  'Декабрь',
];

const DAY_MS = 86_400_000;

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

/** Разбирает `YYYY-MM-DD` в UTC-полночь. */
export function parseIsoDate(iso: string): Date {
  const parts = iso.slice(0, 10).split('-');
  const year = Number(parts[0] ?? 0);
  const month = Number(parts[1] ?? 1);
  const day = Number(parts[2] ?? 1);
  return new Date(Date.UTC(year, month - 1, day));
}

/** `YYYY-MM-DD` → `dd.mm.yyyy`. */
export function formatDate(iso: string): string {
  const parts = iso.slice(0, 10).split('-');
  const year = parts[0] ?? '';
  const month = parts[1] ?? '';
  const day = parts[2] ?? '';
  return `${day}.${month}.${year}`;
}

/** Полночь текущей локальной даты в UTC-миллисекундах (только для разницы дат). */
function todayUtcMs(now: Date): number {
  return Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
}

/** Число календарных дней от сегодня до даты (отрицательное — дата в прошлом). */
export function daysUntil(iso: string, now: Date = new Date()): number {
  return Math.round((parseIsoDate(iso).getTime() - todayUtcMs(now)) / DAY_MS);
}

/** Текущая локальная дата в формате `YYYY-MM-DD`. */
export function todayIso(now: Date = new Date()): string {
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** Первое и последнее число месяца `YYYY-MM`. */
export function monthRange(month: string): { from: string; to: string } {
  const parts = month.split('-');
  const year = Number(parts[0] ?? 0);
  const monthIndex = Number(parts[1] ?? 1);
  const lastDay = new Date(Date.UTC(year, monthIndex, 0)).getUTCDate();
  return {
    from: `${month}-01`,
    to: `${month}-${pad(lastDay)}`,
  };
}

/** Сдвиг месяца `YYYY-MM` на delta месяцев. */
export function addMonths(month: string, delta: number): string {
  const parts = month.split('-');
  const year = Number(parts[0] ?? 0);
  const monthIndex = Number(parts[1] ?? 1);
  const shifted = new Date(Date.UTC(year, monthIndex - 1 + delta, 1));
  return `${shifted.getUTCFullYear()}-${pad(shifted.getUTCMonth() + 1)}`;
}

/** `YYYY-MM` → «Октябрь 2026». */
export function monthTitle(month: string): string {
  const parts = month.split('-');
  const year = Number(parts[0] ?? 0);
  const monthIndex = Number(parts[1] ?? 1);
  return `${MONTH_NAMES[monthIndex - 1] ?? ''} ${year}`;
}

/** Русская плюрализация: plural(3, ['день', 'дня', 'дней']) → 'дня'. */
export function plural(number: number, forms: readonly [string, string, string]): string {
  const abs = Math.abs(number);
  const tail = abs % 100;
  if (tail >= 11 && tail <= 14) {
    return forms[2];
  }
  const last = abs % 10;
  if (last === 1) {
    return forms[0];
  }
  if (last >= 2 && last <= 4) {
    return forms[1];
  }
  return forms[2];
}

/** «21 день», «2 дня», «7 дней». */
export function formatDaysLabel(days: number): string {
  return `${days} ${plural(days, ['день', 'дня', 'дней'])}`;
}

/**
 * «обновлено N назад» по ISO-метке. `null`/невалидная метка → null
 * (индикатор скрывается, см. ui «индикация сроков», §6).
 */
export function formatFreshness(iso: string | null, now: number = Date.now()): string | null {
  if (!iso) {
    return null;
  }
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) {
    return null;
  }
  const minutes = Math.max(0, Math.floor((now - timestamp) / 60_000));
  if (minutes < 1) {
    return 'обновлено только что';
  }
  if (minutes < 60) {
    return `обновлено ${minutes} ${plural(minutes, ['минуту', 'минуты', 'минут'])} назад`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `обновлено ${hours} ${plural(hours, ['час', 'часа', 'часов'])} назад`;
  }
  const days = Math.floor(hours / 24);
  return `обновлено ${days} ${plural(days, ['день', 'дня', 'дней'])} назад`;
}

/** Минимальная ISO-метка среди непустых; null, если меток нет. */
export function minTimestamp(values: Array<string | null | undefined>): string | null {
  let min: number | null = null;
  for (const value of values) {
    if (!value) {
      continue;
    }
    const ts = Date.parse(value);
    if (Number.isNaN(ts)) {
      continue;
    }
    if (min === null || ts < min) {
      min = ts;
    }
  }
  return min === null ? null : new Date(min).toISOString();
}
