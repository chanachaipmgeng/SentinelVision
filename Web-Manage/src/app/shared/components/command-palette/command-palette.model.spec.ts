import { Menu } from '../../services/nav.service';
import { filterPaletteEntries, flattenMenu, isTypingTarget } from './command-palette.model';

describe('command palette model', () => {
  const th: Record<string, string> = {
    'Overview dashboard': 'แดชบอร์ดภาพรวม',
    'Attendance module': 'โมดูลลงเวลา',
    'Attendance history': 'ประวัติการลงเวลา',
    'Approval inbox': 'กล่องอนุมัติ',
    'Audit log': 'บันทึกการตรวจสอบ',
  };

  const menu: Menu[] = [
    { headTitle: 'SENTINELVISION COMMAND' },
    { path: '/company/dashboard', title: 'Overview dashboard', type: 'link', icon: 'home' },
    {
      title: 'Attendance module',
      type: 'sub',
      children: [
        { path: '/company/timestamp-log', title: 'Attendance history', type: 'link' },
        { path: '/company/approval-inbox', title: 'Approval inbox', type: 'link' },
      ],
    },
    { path: '/company/audit-log', title: 'Audit log', type: 'link' },
    { path: '/company/dashboard', title: 'Overview dashboard', type: 'link' },
  ];

  const entriesFor = (lang: 'en' | 'th') =>
    flattenMenu(
      menu,
      (k) => (lang === 'th' ? th[k] || k : k),
      (k) => [th[k]].filter(Boolean) as string[],
    );

  it('flattens children, skips headings/sub parents and de-duplicates paths', () => {
    const entries = entriesFor('en');
    expect(entries.map((e) => e.path)).toEqual([
      '/company/dashboard',
      '/company/timestamp-log',
      '/company/approval-inbox',
      '/company/audit-log',
    ]);
    expect(entries[1].section).toBe('Attendance module');
    expect(entries[0].section).toBe('SENTINELVISION COMMAND');
  });

  it('matches English titles and paths regardless of the UI language', () => {
    const entries = entriesFor('th');
    expect(filterPaletteEntries(entries, 'approval').map((e) => e.path)).toEqual([
      '/company/approval-inbox',
    ]);
    expect(filterPaletteEntries(entries, 'timestamp').map((e) => e.path)).toEqual([
      '/company/timestamp-log',
    ]);
  });

  it('matches Thai titles while the UI is in English', () => {
    const entries = entriesFor('en');
    expect(filterPaletteEntries(entries, 'อนุมัติ').map((e) => e.path)).toEqual([
      '/company/approval-inbox',
    ]);
  });

  it('requires every token and ranks label prefix matches first', () => {
    const entries = entriesFor('en');
    expect(filterPaletteEntries(entries, 'attendance history').map((e) => e.path)).toEqual([
      '/company/timestamp-log',
    ]);
    const ranked = filterPaletteEntries(entries, 'a').map((e) => e.path);
    expect(ranked[0]).toBe('/company/timestamp-log');
    expect(filterPaletteEntries(entries, 'zzz-not-there')).toEqual([]);
  });

  it('only lists what the (already permission-filtered) menu contains', () => {
    const limited = flattenMenu([menu[1]], (k) => k, () => []);
    expect(filterPaletteEntries(limited, 'audit')).toEqual([]);
  });

  it('returns the first entries for an empty query, honoring the limit', () => {
    expect(filterPaletteEntries(entriesFor('en'), '', 2).length).toBe(2);
  });

  it('detects typing targets', () => {
    expect(isTypingTarget(document.createElement('input'))).toBeTrue();
    expect(isTypingTarget(document.createElement('textarea'))).toBeTrue();
    expect(isTypingTarget(document.createElement('div'))).toBeFalse();
    expect(isTypingTarget(null)).toBeFalse();
  });
});
