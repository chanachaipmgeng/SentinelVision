import { Injectable } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

/** Formats dates/numbers according to the active ngx-translate language (th → th-TH, en → en-GB). */
@Injectable({ providedIn: 'root' })
export class LocaleFormatService {
  constructor(private readonly translate: TranslateService) {}

  localeTag(): string {
    const lang = (this.translate.currentLang || this.translate.defaultLang || 'th').toLowerCase();
    return lang.startsWith('en') ? 'en-GB' : 'th-TH';
  }

  formatDate(
    value: Date | string | number | null | undefined,
    options: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    },
  ): string {
    if (value == null || value === '') {
      return '';
    }
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) {
      return String(value);
    }
    return new Intl.DateTimeFormat(this.localeTag(), options).format(date);
  }

  formatDateTime(value: Date | string | number | null | undefined): string {
    return this.formatDate(value, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  }

  formatNumber(
    value: number | string | null | undefined,
    options?: Intl.NumberFormatOptions,
  ): string {
    if (value == null || value === '') {
      return '';
    }
    const n = typeof value === 'number' ? value : Number(value);
    if (!Number.isFinite(n)) {
      return String(value);
    }
    return new Intl.NumberFormat(this.localeTag(), options).format(n);
  }
}
