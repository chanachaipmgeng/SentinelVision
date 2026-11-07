/** Pure helpers for shared DataTable server-side pagination / filter / sort (Phase E2). */

export type SortDir = 'asc' | 'desc';

export interface DataTableQuery {
  limit: number;
  offset: number;
  pageIndex: number;
  pageSize: number;
  q?: string;
  sortBy?: string;
  sortDir?: SortDir;
}

export interface PageEnvelope<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface DataTableQueryInput {
  pageIndex?: number;
  pageSize?: number;
  q?: string | null;
  sortBy?: string | null;
  sortDir?: SortDir | string | null;
  /** Hard cap for pageSize (default 100). */
  maxPageSize?: number;
}

/** Normalize UI pager state into API limit/offset (+ optional q/sort). */
export function buildDataTableQuery(input: DataTableQueryInput = {}): DataTableQuery {
  const maxPageSize = Math.max(1, input.maxPageSize ?? 100);
  const pageSize = Math.min(Math.max(1, Math.floor(input.pageSize ?? 10)), maxPageSize);
  const pageIndex = Math.max(0, Math.floor(input.pageIndex ?? 0));
  const q = (input.q ?? '').toString().trim();
  const sortBy = (input.sortBy ?? '').toString().trim() || undefined;
  const rawDir = (input.sortDir ?? 'asc').toString().toLowerCase();
  const sortDir: SortDir | undefined = sortBy
    ? rawDir === 'desc'
      ? 'desc'
      : 'asc'
    : undefined;

  return {
    limit: pageSize,
    offset: pageIndex * pageSize,
    pageIndex,
    pageSize,
    q: q || undefined,
    sortBy,
    sortDir,
  };
}

/** Build HttpParams-friendly record (omits empty optional fields). Always sets paged=1. */
export function toDataTableParams(
  query: DataTableQuery,
  extra: Record<string, string | number | boolean | null | undefined> = {},
): Record<string, string> {
  const params: Record<string, string> = {
    paged: '1',
    limit: String(query.limit),
    offset: String(query.offset),
  };
  if (query.q) params['q'] = query.q;
  if (query.sortBy) {
    params['sort_by'] = query.sortBy;
    params['sort_dir'] = query.sortDir || 'asc';
  }
  for (const [key, value] of Object.entries(extra)) {
    if (value === null || value === undefined || value === '') continue;
    params[key] = String(value);
  }
  return params;
}

/** Accept either a legacy bare array or a Phase E2 page envelope. */
export function normalizePageEnvelope<T>(payload: PageEnvelope<T> | T[] | null | undefined): PageEnvelope<T> {
  if (Array.isArray(payload)) {
    return {
      items: payload,
      total: payload.length,
      limit: payload.length,
      offset: 0,
    };
  }
  const items = Array.isArray(payload?.items) ? payload!.items : [];
  return {
    items,
    total: Math.max(0, Number(payload?.total ?? items.length) || 0),
    limit: Math.max(0, Number(payload?.limit ?? items.length) || 0),
    offset: Math.max(0, Number(payload?.offset ?? 0) || 0),
  };
}

/** Clamp pageIndex after total/pageSize changes (e.g. filter shrinks result set). */
export function clampPageIndex(pageIndex: number, total: number, pageSize: number): number {
  const size = Math.max(1, pageSize || 1);
  const maxPage = Math.max(0, Math.ceil(Math.max(0, total) / size) - 1);
  return Math.max(0, Math.min(Math.floor(pageIndex || 0), maxPage));
}
