import { Pipe, PipeTransform } from '@angular/core';
import { LocaleFormatService } from '../services/locale-format.service';

@Pipe({ name: 'localeDate', standalone: true, pure: false })
export class LocaleDatePipe implements PipeTransform {
  constructor(private readonly localeFormat: LocaleFormatService) {}

  transform(
    value: Date | string | number | null | undefined,
    mode: 'date' | 'datetime' = 'date',
  ): string {
    return mode === 'datetime'
      ? this.localeFormat.formatDateTime(value)
      : this.localeFormat.formatDate(value);
  }
}
