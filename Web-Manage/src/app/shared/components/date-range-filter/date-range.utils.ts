/**
 * Calendar-date helpers for list filters. Dates are `YYYY-MM-DD` strings interpreted in
 * Asia/Bangkok (UTC+7, no DST), matching the API's attendance/export day boundaries.
 */
export const BANGKOK_TZ = 'Asia/Bangkok';
const BANGKOK_OFFSET = '+07:00';

export type DateRangePreset =
  | 'today'
  | 'yesterday'
  | 'last7'
  | 'thisMonth'
  | 'lastMonth'
  | 'custom';

export const DATE_RANGE_PRESETS: DateRangePreset[] = [
  'today',
  'yesterday',
  'last7',
  'thisMonth',
  'lastMonth',
  'custom',
];

export interface DateRangeValue {
  from: string;
  to: string;
  preset?: DateRangePreset;
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function isIsoDate(value: unknown): value is string {
  return typeof value === 'string' && ISO_DATE.test(value);
}

/** Today's calendar date in Bangkok, regardless of the browser time zone. */
export function bangkokToday(now: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: BANGKOK_TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(now);
  const get = (type: string) => parts.find((p) => p.type === type)?.value || '';
  return `${get('year')}-${get('month')}-${get('day')}`;
}

function toUtcDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

function fromUtcDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function addDays(iso: string, days: number): string {
  const d = toUtcDate(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return fromUtcDate(d);
}

export function startOfMonth(iso: string): string {
  return `${iso.slice(0, 7)}-01`;
}

export function endOfMonth(iso: string): string {
  const [y, m] = iso.split('-').map(Number);
  return fromUtcDate(new Date(Date.UTC(y, m, 0)));
}

/** Resolves a relative preset against `today` (Bangkok). Returns null for `custom`. */
export function resolvePreset(
  preset: DateRangePreset,
  today: string = bangkokToday()
): DateRangeValue | null {
  switch (preset) {
    case 'today':
      return { from: today, to: today, preset };
    case 'yesterday': {
      const y = addDays(today, -1);
      return { from: y, to: y, preset };
    }
    case 'last7':
      return { from: addDays(today, -6), to: today, preset };
    case 'thisMonth':
      return { from: startOfMonth(today), to: endOfMonth(today), preset };
    case 'lastMonth': {
      const prev = addDays(startOfMonth(today), -1);
      return { from: startOfMonth(prev), to: endOfMonth(prev), preset };
    }
    default:
      return null;
  }
}

/** Finds the preset whose resolved range equals `range`, else `custom`. */
export function detectPreset(
  range: { from: string; to: string },
  today: string = bangkokToday()
): DateRangePreset {
  for (const preset of DATE_RANGE_PRESETS) {
    const r = resolvePreset(preset, today);
    if (r && r.from === range.from && r.to === range.to) return preset;
  }
  return 'custom';
}

/** Orders the bounds so `from <= to`; ISO date strings compare lexicographically. */
export function normalizeRange(range: DateRangeValue): DateRangeValue {
  if (range.from && range.to && range.from > range.to) {
    return { ...range, from: range.to, to: range.from };
  }
  return range;
}

/**
 * Re-resolves a relative preset (e.g. a saved "this month" view stays "this month") and
 * falls back to `fallback` when the stored value is unusable.
 */
export function refreshRange(
  range: Partial<DateRangeValue> | null | undefined,
  fallback: DateRangePreset = 'thisMonth',
  today: string = bangkokToday()
): DateRangeValue {
  if (range?.preset && range.preset !== 'custom') {
    return resolvePreset(range.preset, today)!;
  }
  if (isIsoDate(range?.from) && isIsoDate(range?.to)) {
    return normalizeRange({ from: range!.from!, to: range!.to!, preset: 'custom' });
  }
  return resolvePreset(fallback, today) || { from: today, to: today, preset: 'today' };
}

/** Inclusive Bangkok day bounds as instants: `from` 00:00:00.000 → `to` 23:59:59.999 (+07:00). */
export function bangkokRangeToInstants(range: { from: string; to: string }): {
  start: Date;
  end: Date;
} {
  return {
    start: new Date(`${range.from}T00:00:00.000${BANGKOK_OFFSET}`),
    end: new Date(`${range.to}T23:59:59.999${BANGKOK_OFFSET}`),
  };
}
