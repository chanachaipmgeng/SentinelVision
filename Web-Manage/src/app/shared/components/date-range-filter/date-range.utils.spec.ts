import {
  addDays,
  bangkokRangeToInstants,
  bangkokToday,
  detectPreset,
  endOfMonth,
  normalizeRange,
  refreshRange,
  resolvePreset,
} from './date-range.utils';

describe('date-range utils (Asia/Bangkok)', () => {
  it('bangkokToday uses Bangkok, not the browser zone', () => {
    // 2026-03-31T18:30Z is already 2026-04-01 01:30 in Bangkok.
    expect(bangkokToday(new Date('2026-03-31T18:30:00Z'))).toBe('2026-04-01');
    // 2026-04-01T16:59Z is 23:59 Bangkok — still the same day.
    expect(bangkokToday(new Date('2026-04-01T16:59:00Z'))).toBe('2026-04-01');
  });

  it('addDays / endOfMonth handle month, year and leap boundaries', () => {
    expect(addDays('2026-01-01', -1)).toBe('2025-12-31');
    expect(addDays('2028-02-28', 1)).toBe('2028-02-29');
    expect(endOfMonth('2026-02-10')).toBe('2026-02-28');
    expect(endOfMonth('2028-02-10')).toBe('2028-02-29');
  });

  describe('resolvePreset', () => {
    const today = '2026-03-05';

    it('today / yesterday', () => {
      expect(resolvePreset('today', today)).toEqual({ from: today, to: today, preset: 'today' });
      expect(resolvePreset('yesterday', today)).toEqual({ from: '2026-03-04', to: '2026-03-04', preset: 'yesterday' });
    });

    it('last 7 days includes today', () => {
      expect(resolvePreset('last7', today)).toEqual({ from: '2026-02-27', to: today, preset: 'last7' });
    });

    it('this month / last month', () => {
      expect(resolvePreset('thisMonth', today)).toEqual({ from: '2026-03-01', to: '2026-03-31', preset: 'thisMonth' });
      expect(resolvePreset('lastMonth', today)).toEqual({ from: '2026-02-01', to: '2026-02-28', preset: 'lastMonth' });
      expect(resolvePreset('lastMonth', '2026-01-15')).toEqual({
        from: '2025-12-01',
        to: '2025-12-31',
        preset: 'lastMonth',
      });
    });

    it('custom has no resolved range', () => {
      expect(resolvePreset('custom', today)).toBeNull();
    });
  });

  it('detectPreset matches resolved ranges, else custom', () => {
    const today = '2026-03-05';
    expect(detectPreset({ from: '2026-03-05', to: '2026-03-05' }, today)).toBe('today');
    expect(detectPreset({ from: '2026-03-01', to: '2026-03-31' }, today)).toBe('thisMonth');
    expect(detectPreset({ from: '2026-03-02', to: '2026-03-03' }, today)).toBe('custom');
  });

  it('normalizeRange swaps reversed bounds', () => {
    expect(normalizeRange({ from: '2026-03-10', to: '2026-03-01' })).toEqual({ from: '2026-03-01', to: '2026-03-10' });
  });

  it('refreshRange re-resolves relative presets and keeps custom dates', () => {
    const today = '2026-04-20';
    expect(refreshRange({ preset: 'thisMonth', from: '2026-03-01', to: '2026-03-31' }, 'thisMonth', today)).toEqual({
      from: '2026-04-01',
      to: '2026-04-30',
      preset: 'thisMonth',
    });
    expect(refreshRange({ from: '2026-01-09', to: '2026-01-02', preset: 'custom' }, 'thisMonth', today)).toEqual({
      from: '2026-01-02',
      to: '2026-01-09',
      preset: 'custom',
    });
    expect(refreshRange(null, 'today', today)).toEqual({ from: today, to: today, preset: 'today' });
  });

  it('bangkokRangeToInstants spans whole Bangkok days', () => {
    const { start, end } = bangkokRangeToInstants({ from: '2026-03-01', to: '2026-03-31' });
    expect(start.toISOString()).toBe('2026-02-28T17:00:00.000Z');
    expect(end.toISOString()).toBe('2026-03-31T16:59:59.999Z');
  });
});
