import { Pipe, PipeTransform } from '@angular/core';
import { LocaleFormatService } from '../services/locale-format.service';

@Pipe({ name: 'localeNumber', standalone: true, pure: false })
export class LocaleNumberPipe implements PipeTransform {
  constructor(private readonly localeFormat: LocaleFormatService) {}

  transform(
    value: number | string | null | undefined,
    digits: number | null = null,
  ): string {
    const options: Intl.NumberFormatOptions | undefined =
      digits == null
        ? undefined
        : { minimumFractionDigits: digits, maximumFractionDigits: digits };
    return this.localeFormat.formatNumber(value, options);
  }
}
