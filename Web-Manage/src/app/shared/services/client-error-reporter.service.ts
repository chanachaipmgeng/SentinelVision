import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { TokenService } from './token.service';

const REPORTABLE = new Set([0, 400, 409, 422]);
const SKIP_PATH = '/system/client-errors';

export interface ClientErrorReport {
  message: string;
  statusCode: number;
  method?: string;
  path?: string;
  pageUrl?: string;
  requestId?: string;
  errorCode?: string;
  companyId?: string;
}

@Injectable({ providedIn: 'root' })
export class ClientErrorReporterService {
  private recent = new Map<string, number>();

  constructor(private tokenService: TokenService) {}

  shouldReport(status: number): boolean {
    if (status >= 500) return true;
    return REPORTABLE.has(status);
  }

  reportFromHttpError(error: HttpErrorResponse, method?: string, requestUrl?: string): void {
    if (!(error instanceof HttpErrorResponse)) return;
    if (!this.shouldReport(error.status)) return;

    const url = requestUrl || error.url || '';
    if (url.includes(SKIP_PATH)) return;

    const path = this.toApiPath(url);
    const body = this.asRecord(error.error);
    const nested = this.asRecord(body?.['error']);
    const requestId =
      (typeof nested?.['requestId'] === 'string' && nested['requestId']) ||
      (typeof body?.['requestId'] === 'string' && body['requestId']) ||
      undefined;
    const errorCode =
      (typeof nested?.['code'] === 'string' && nested['code']) || undefined;
    const message =
      (typeof nested?.['message'] === 'string' && nested['message']) ||
      (typeof body?.['message'] === 'string' && body['message']) ||
      (typeof body?.['detail'] === 'string' && body['detail']) ||
      error.message ||
      'Request failed';

    const companyId = this.tokenService.getSelectCompany()?.companyId || undefined;
    this.report({
      message: String(message).slice(0, 2000),
      statusCode: error.status || 0,
      method: method || undefined,
      path: path.slice(0, 500) || undefined,
      pageUrl: typeof window !== 'undefined' ? window.location.href.slice(0, 1000) : undefined,
      requestId: requestId ? String(requestId).slice(0, 64) : undefined,
      errorCode: errorCode ? String(errorCode).slice(0, 64) : undefined,
      companyId,
    });
  }

  report(payload: ClientErrorReport): void {
    const raw = this.tokenService.getToken();
    if (!raw) return;

    const key = `${payload.statusCode}|${payload.method || ''}|${payload.path || ''}|${payload.message}`;
    const now = Date.now();
    const last = this.recent.get(key) || 0;
    if (now - last < 3000) return;
    this.recent.set(key, now);
    if (this.recent.size > 200) {
      for (const [k, t] of this.recent) {
        if (now - t > 60_000) this.recent.delete(k);
      }
    }

    const token = raw.startsWith('Bearer ') ? raw : `Bearer ${raw}`;
    const endpoint = `${environment.baseUrl || ''}${SKIP_PATH}`;
    // fetch bypasses HttpRequestInterceptor — avoids recursive error reporting.
    void fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token,
      },
      credentials: 'include',
      body: JSON.stringify(payload),
    }).catch(() => undefined);
  }

  private toApiPath(fullUrl: string): string {
    try {
      if (fullUrl.startsWith('http')) {
        const u = new URL(fullUrl);
        return u.pathname;
      }
    } catch {
      /* ignore */
    }
    const base = environment.baseUrl || '';
    if (base && fullUrl.startsWith(base)) {
      return fullUrl.slice(base.length).split('?')[0];
    }
    return fullUrl.split('?')[0];
  }

  private asRecord(value: unknown): Record<string, unknown> | null {
    return value && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : null;
  }
}
