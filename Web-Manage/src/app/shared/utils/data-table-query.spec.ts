import {
  buildDataTableQuery,
  clampPageIndex,
  normalizePageEnvelope,
  toDataTableParams,
} from './data-table-query';

describe('data-table-query helpers', () => {
  describe('buildDataTableQuery', () => {
    it('maps pageIndex/pageSize to limit/offset', () => {
      expect(buildDataTableQuery({ pageIndex: 2, pageSize: 25 })).toEqual({
        limit: 25,
        offset: 50,
        pageIndex: 2,
        pageSize: 25,
        q: undefined,
        sortBy: undefined,
        sortDir: undefined,
      });
    });

    it('trims q and normalizes sort', () => {
      const q = buildDataTableQuery({
        pageIndex: 0,
        pageSize: 10,
        q: '  alice  ',
        sortBy: 'name',
        sortDir: 'DESC',
      });
      expect(q.q).toBe('alice');
      expect(q.sortBy).toBe('name');
      expect(q.sortDir).toBe('desc');
    });

    it('caps pageSize and floors negatives', () => {
      expect(buildDataTableQuery({ pageIndex: -3, pageSize: 999, maxPageSize: 50 })).toEqual(
        jasmine.objectContaining({ pageIndex: 0, pageSize: 50, limit: 50, offset: 0 }),
      );
    });

    it('omits sortDir when sortBy is empty', () => {
      const q = buildDataTableQuery({ sortBy: '  ', sortDir: 'desc' });
      expect(q.sortBy).toBeUndefined();
      expect(q.sortDir).toBeUndefined();
    });
  });

  describe('toDataTableParams', () => {
    it('always sets paged=1 and skips empty extras', () => {
      const query = buildDataTableQuery({ pageIndex: 1, pageSize: 10, q: 'x', sortBy: 'occurredAt', sortDir: 'desc' });
      expect(
        toDataTableParams(query, {
          company_employeeId: '',
          timestampType: 1,
          startDate: undefined,
        }),
      ).toEqual({
        paged: '1',
        limit: '10',
        offset: '10',
        q: 'x',
        sort_by: 'occurredAt',
        sort_dir: 'desc',
        timestampType: '1',
      });
    });
  });

  describe('normalizePageEnvelope', () => {
    it('wraps legacy arrays', () => {
      expect(normalizePageEnvelope([{ id: 1 }, { id: 2 }])).toEqual({
        items: [{ id: 1 }, { id: 2 }],
        total: 2,
        limit: 2,
        offset: 0,
      });
    });

    it('passes through page envelopes', () => {
      expect(
        normalizePageEnvelope({ items: ['a'], total: 9, limit: 1, offset: 3 }),
      ).toEqual({ items: ['a'], total: 9, limit: 1, offset: 3 });
    });

    it('handles nullish payload', () => {
      expect(normalizePageEnvelope(null)).toEqual({
        items: [],
        total: 0,
        limit: 0,
        offset: 0,
      });
    });
  });

  describe('clampPageIndex', () => {
    it('clamps to last valid page', () => {
      expect(clampPageIndex(99, 25, 10)).toBe(2);
      expect(clampPageIndex(-1, 25, 10)).toBe(0);
      expect(clampPageIndex(1, 0, 10)).toBe(0);
    });
  });
});
