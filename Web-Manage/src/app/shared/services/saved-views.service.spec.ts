import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import {
  SAVED_VIEWS_MAX_PER_PAGE,
  SavedViewsScope,
  SavedViewsService,
  stableStringify,
} from './saved-views.service';

describe('SavedViewsService', () => {
  const scope: SavedViewsScope = { companyId: 'c1', pageKey: 'timestamp-log' };
  let service: SavedViewsService;

  beforeEach(() => {
    window.localStorage.clear();
    TestBed.configureTestingModule({});
    service = TestBed.inject(SavedViewsService);
  });

  afterEach(() => window.localStorage.clear());

  it('stores views under sv_views:{companyId}:{pageKey}', async () => {
    await firstValueFrom(service.create(scope, 'Late this month', { status: '1' }));
    const raw = window.localStorage.getItem('sv_views:c1:timestamp-log');
    expect(raw).toBeTruthy();
    expect(JSON.parse(raw!)[0].name).toBe('Late this month');
  });

  it('isolates views per company and page', async () => {
    await firstValueFrom(service.create(scope, 'A', { q: 'a' }));
    await firstValueFrom(service.create({ companyId: 'c2', pageKey: 'timestamp-log' }, 'B', {}));
    await firstValueFrom(service.create({ companyId: 'c1', pageKey: 'access-logs' }, 'C', {}));
    const views = await firstValueFrom(service.list(scope));
    expect(views.map((v) => v.name)).toEqual(['A']);
  });

  it('deep-copies filters so later mutations do not leak into storage', async () => {
    const filters = { range: { preset: 'thisMonth' } };
    await firstValueFrom(service.create(scope, 'Month', filters));
    filters.range.preset = 'today';
    const [view] = await firstValueFrom(service.list<typeof filters>(scope));
    expect(view.filters.range.preset).toBe('thisMonth');
  });

  it('trims and collapses names and rejects blank ones', async () => {
    const v = await firstValueFrom(service.create(scope, '   My   view  ', {}));
    expect(v.name).toBe('My view');
    await expectAsync(firstValueFrom(service.create(scope, '   ', {}))).toBeRejectedWithError('name_required');
  });

  it('renames a view', async () => {
    const v = await firstValueFrom(service.create(scope, 'Old', {}));
    await firstValueFrom(service.rename(scope, v.id, 'New'));
    const [view] = await firstValueFrom(service.list(scope));
    expect(view.name).toBe('New');
    await expectAsync(firstValueFrom(service.rename(scope, 'missing', 'x'))).toBeRejectedWithError('not_found');
  });

  it('keeps a single default and can clear it', async () => {
    const a = await firstValueFrom(service.create(scope, 'A', { q: 'a' }));
    const b = await firstValueFrom(service.create(scope, 'B', { q: 'b' }));
    await firstValueFrom(service.setDefault(scope, a.id));
    await firstValueFrom(service.setDefault(scope, b.id));
    const views = await firstValueFrom(service.list(scope));
    expect(views.filter((v) => v.isDefault).map((v) => v.id)).toEqual([b.id]);
    expect((await firstValueFrom(service.getDefault(scope)))?.id).toBe(b.id);

    await firstValueFrom(service.setDefault(scope, null));
    expect(await firstValueFrom(service.getDefault(scope))).toBeNull();
  });

  it('removes views and clears the key when the last one is deleted', async () => {
    const v = await firstValueFrom(service.create(scope, 'Only', {}));
    await firstValueFrom(service.remove(scope, v.id));
    expect(await firstValueFrom(service.list(scope))).toEqual([]);
    expect(window.localStorage.getItem('sv_views:c1:timestamp-log')).toBeNull();
  });

  it('enforces the per-page limit', async () => {
    for (let i = 0; i < SAVED_VIEWS_MAX_PER_PAGE; i++) {
      await firstValueFrom(service.create(scope, `V${i}`, {}));
    }
    await expectAsync(firstValueFrom(service.create(scope, 'overflow', {}))).toBeRejectedWithError('limit_reached');
  });

  it('ignores corrupt storage', async () => {
    window.localStorage.setItem('sv_views:c1:timestamp-log', '{not json');
    expect(await firstValueFrom(service.list(scope))).toEqual([]);
    window.localStorage.setItem('sv_views:c1:timestamp-log', JSON.stringify([{ bogus: true }]));
    expect(await firstValueFrom(service.list(scope))).toEqual([]);
  });

  it('stableStringify ignores key order and undefined values', () => {
    expect(stableStringify({ b: 1, a: { d: 2, c: [1, { y: 1, x: 2 }] } })).toBe(
      stableStringify({ a: { c: [1, { x: 2, y: 1 }], d: 2 }, b: 1, z: undefined })
    );
    expect(stableStringify({ a: 1 })).not.toBe(stableStringify({ a: '1' }));
  });
});
