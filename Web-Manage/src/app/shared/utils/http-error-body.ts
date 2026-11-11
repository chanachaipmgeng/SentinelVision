import { HttpErrorResponse } from '@angular/common/http';
import { isRecord } from './type-guards';

/** Typical FastAPI / DPU error JSON shape. */
export interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
  message?: string;
  error?: string;
}

export function errorBodyFromHttp(err: unknown): ApiErrorBody | null {
  if (!(err instanceof HttpErrorResponse)) return null;
  const body = err.error;
  return isRecord(body) ? (body as ApiErrorBody) : null;
}

export function apiErrorMessage(err: unknown, fallback = 'Request failed'): string {
  const body = errorBodyFromHttp(err);
  if (!body) {
    return err instanceof HttpErrorResponse ? err.message || fallback : fallback;
  }
  if (typeof body.message === 'string' && body.message) return body.message;
  if (typeof body.error === 'string' && body.error) return body.error;
  if (typeof body.detail === 'string' && body.detail) return body.detail;
  if (Array.isArray(body.detail) && body.detail[0]?.msg) {
    return String(body.detail[0].msg);
  }
  return fallback;
}
