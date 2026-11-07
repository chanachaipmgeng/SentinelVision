import { Injectable, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Subject } from 'rxjs';

/**
 * Loads protected `/images/<file>` through HttpClient (Bearer header via the interceptor) and
 * hands back a blob URL for `<img src>`. Replaces the old `?token=` query-string trick, which
 * leaked the JWT into proxy and browser logs.
 */
@Injectable({ providedIn: 'root' })
export class AuthedImageService implements OnDestroy {
  private readonly cache = new Map<string, string>();
  private readonly pending = new Set<string>();
  private readonly maxEntries = 300;
  /** Emits the file name once its blob URL is ready so views can re-render. */
  readonly loaded$ = new Subject<string>();

  constructor(private http: HttpClient) {}

  /**
   * Synchronous accessor for templates: returns the cached blob URL, or `placeholder` while the
   * image is being fetched (the fetch is started on first call).
   */
  urlFor(file: string | null | undefined, placeholder = ''): string {
    if (!file) {
      return placeholder;
    }
    const hit = this.cache.get(file);
    if (hit) {
      return hit;
    }
    if (!this.pending.has(file)) {
      this.pending.add(file);
      const path = `/images/${file}`.replace(/([^:]\/)\/+/g, '$1');
      this.http.get(path, { responseType: 'blob' }).subscribe({
        next: (blob) => {
          this.pending.delete(file);
          this.store(file, URL.createObjectURL(blob));
          this.loaded$.next(file);
        },
        error: () => {
          this.pending.delete(file);
          if (placeholder) {
            this.store(file, placeholder);
            this.loaded$.next(file);
          }
        },
      });
    }
    return placeholder;
  }

  private store(file: string, url: string): void {
    if (this.cache.size >= this.maxEntries) {
      const oldest = this.cache.keys().next().value as string | undefined;
      if (oldest) {
        this.release(oldest);
      }
    }
    this.cache.set(file, url);
  }

  private release(file: string): void {
    const url = this.cache.get(file);
    if (url && url.startsWith('blob:')) {
      URL.revokeObjectURL(url);
    }
    this.cache.delete(file);
  }

  ngOnDestroy(): void {
    for (const file of Array.from(this.cache.keys())) {
      this.release(file);
    }
  }
}
