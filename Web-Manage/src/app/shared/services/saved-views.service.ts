import { Injectable } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';

export interface SavedView<T = unknown> {
  id: string;
  name: string;
  filters: T;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SavedViewsScope {
  companyId: string;
  pageKey: string;
}

export const SAVED_VIEWS_MAX_PER_PAGE = 20;
export const SAVED_VIEW_NAME_MAX = 40;

/**
 * Named filter presets per company + list page.
 *
 * Every method returns an Observable so a backend implementation can be swapped in with
 * `{ provide: SavedViewsService, useClass: ApiSavedViewsService }` without touching callers.
 * This default implementation persists to localStorage under `sv_views:{companyId}:{pageKey}`.
 */
@Injectable({ providedIn: 'root' })
export class SavedViewsService {
  static storageKey(scope: SavedViewsScope): string {
    return `sv_views:${scope.companyId || '_'}:${scope.pageKey}`;
  }

  list<T = unknown>(scope: SavedViewsScope): Observable<SavedView<T>[]> {
    return of(this.read<T>(scope));
  }

  getDefault<T = unknown>(scope: SavedViewsScope): Observable<SavedView<T> | null> {
    return of(this.read<T>(scope).find((v) => v.isDefault) || null);
  }

  create<T = unknown>(scope: SavedViewsScope, name: string, filters: T): Observable<SavedView<T>> {
    const clean = this.cleanName(name);
    if (!clean) return throwError(() => new Error('name_required'));
    const views = this.read<T>(scope);
    if (views.length >= SAVED_VIEWS_MAX_PER_PAGE) {
      return throwError(() => new Error('limit_reached'));
    }
    const now = new Date().toISOString();
    const view: SavedView<T> = {
      id: this.newId(),
      name: clean,
      filters: this.clone(filters),
      isDefault: false,
      createdAt: now,
      updatedAt: now,
    };
    this.write(scope, [...views, view]);
    return of(view);
  }

  rename<T = unknown>(scope: SavedViewsScope, id: string, name: string): Observable<SavedView<T>> {
    const clean = this.cleanName(name);
    if (!clean) return throwError(() => new Error('name_required'));
    return this.patch<T>(scope, id, (v) => ({ ...v, name: clean }));
  }

  updateFilters<T = unknown>(scope: SavedViewsScope, id: string, filters: T): Observable<SavedView<T>> {
    return this.patch<T>(scope, id, (v) => ({ ...v, filters: this.clone(filters) }));
  }

  /** Marks `id` as the page default (auto-applied on load); `null` clears the default. */
  setDefault(scope: SavedViewsScope, id: string | null): Observable<SavedView[]> {
    const views = this.read(scope);
    if (id && !views.some((v) => v.id === id)) {
      return throwError(() => new Error('not_found'));
    }
    const next = views.map((v) => ({ ...v, isDefault: !!id && v.id === id }));
    this.write(scope, next);
    return of(next);
  }

  remove(scope: SavedViewsScope, id: string): Observable<void> {
    this.write(
      scope,
      this.read(scope).filter((v) => v.id !== id)
    );
    return of(undefined);
  }

  private patch<T>(
    scope: SavedViewsScope,
    id: string,
    fn: (v: SavedView<T>) => SavedView<T>
  ): Observable<SavedView<T>> {
    const views = this.read<T>(scope);
    const idx = views.findIndex((v) => v.id === id);
    if (idx < 0) return throwError(() => new Error('not_found'));
    const updated = { ...fn(views[idx]), updatedAt: new Date().toISOString() };
    views[idx] = updated;
    this.write(scope, views);
    return of(updated);
  }

  private read<T>(scope: SavedViewsScope): SavedView<T>[] {
    try {
      const raw = localStorage.getItem(SavedViewsService.storageKey(scope));
      const parsed = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(parsed)) return [];
      return parsed.filter(
        (v): v is SavedView<T> =>
          !!v && typeof v.id === 'string' && typeof v.name === 'string' && 'filters' in v
      ).map((v) => ({ ...v, isDefault: !!v.isDefault }));
    } catch {
      return [];
    }
  }

  private write(scope: SavedViewsScope, views: SavedView<unknown>[]): void {
    const key = SavedViewsService.storageKey(scope);
    try {
      if (views.length) localStorage.setItem(key, JSON.stringify(views));
      else localStorage.removeItem(key);
    } catch {
      // Storage full / disabled (private mode): views simply do not persist.
    }
  }

  private cleanName(name: string): string {
    return (name || '').replace(/\s+/g, ' ').trim().slice(0, SAVED_VIEW_NAME_MAX);
  }

  private clone<T>(value: T): T {
    return value === undefined ? value : JSON.parse(JSON.stringify(value));
  }

  private newId(): string {
    const c = (globalThis as any).crypto;
    if (c?.randomUUID) return c.randomUUID();
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  }
}

/** Key-order-independent JSON used to detect which saved view matches the current filters. */
export function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value ?? null);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  const obj = value as Record<string, unknown>;
  return `{${Object.keys(obj)
    .filter((k) => obj[k] !== undefined)
    .sort()
    .map((k) => `${JSON.stringify(k)}:${stableStringify(obj[k])}`)
    .join(',')}}`;
}
