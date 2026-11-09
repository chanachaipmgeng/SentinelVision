import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import {
  DATE_RANGE_PRESETS,
  DateRangePreset,
  DateRangeValue,
  bangkokToday,
  detectPreset,
  isIsoDate,
  normalizeRange,
  resolvePreset,
} from './date-range.utils';

let nextId = 0;

/**
 * Preset chips + from/to date inputs (flatpickr). Emits `{ from, to, preset }` as
 * `YYYY-MM-DD` Bangkok calendar dates; convert with `bangkokRangeToInstants` for API calls.
 */
@Component({
  selector: 'app-date-range-filter',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule, FlatpickrModule],
  providers: [FlatpickrDefaults],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="dpu-drf" role="group" [attr.aria-label]="'listKit.dateRange.label' | translate">
      <div class="dpu-drf__presets" *ngIf="showPresets">
        <button
          *ngFor="let p of presets"
          type="button"
          class="dpu-drf__preset"
          [class.is-active]="current.preset === p"
          [attr.aria-pressed]="current.preset === p"
          (click)="selectPreset(p)">
          {{ 'listKit.dateRange.preset.' + p | translate }}
        </button>
      </div>
      <div class="dpu-drf__inputs">
        <label class="dpu-drf__field">
          <span class="dpu-drf__caption">{{ 'listKit.dateRange.from' | translate }}</span>
          <input
            class="form-control dpu-drf__input"
            [id]="uid + '-from'"
            mwlFlatpickr
            [altInput]="true"
            altFormat="d/m/Y"
            dateFormat="Y-m-d"
            [convertModelValue]="false"
            [ngModel]="current.from"
            (ngModelChange)="onDateInput('from', $event)"
            [attr.aria-label]="'listKit.dateRange.from' | translate" />
        </label>
        <span class="dpu-drf__sep" aria-hidden="true">–</span>
        <label class="dpu-drf__field">
          <span class="dpu-drf__caption">{{ 'listKit.dateRange.to' | translate }}</span>
          <input
            class="form-control dpu-drf__input"
            [id]="uid + '-to'"
            mwlFlatpickr
            [altInput]="true"
            altFormat="d/m/Y"
            dateFormat="Y-m-d"
            [convertModelValue]="false"
            [ngModel]="current.to"
            (ngModelChange)="onDateInput('to', $event)"
            [attr.aria-label]="'listKit.dateRange.to' | translate" />
        </label>
      </div>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
        min-width: 0;
      }
      .dpu-drf {
        display: flex;
        flex-wrap: wrap;
        align-items: flex-end;
        gap: 0.5rem 0.75rem;
      }
      .dpu-drf__presets {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
      }
      .dpu-drf__preset {
        border: 1px solid var(--dpu-border);
        background: var(--dpu-surface-elevated);
        color: var(--dpu-muted);
        border-radius: 999px;
        padding: 0.3rem 0.75rem;
        font-size: 0.78rem;
        font-weight: 600;
        line-height: 1.2;
        cursor: pointer;
        transition: background var(--dpu-duration) var(--dpu-ease),
          color var(--dpu-duration) var(--dpu-ease),
          border-color var(--dpu-duration) var(--dpu-ease);
      }
      .dpu-drf__preset:hover {
        border-color: var(--dpu-brand);
        color: var(--dpu-brand);
      }
      .dpu-drf__preset:focus-visible {
        outline: 2px solid var(--dpu-brand);
        outline-offset: 2px;
      }
      .dpu-drf__preset.is-active {
        background: var(--dpu-brand-soft);
        border-color: var(--dpu-brand);
        color: var(--dpu-brand);
      }
      .dpu-drf__inputs {
        display: flex;
        align-items: flex-end;
        gap: 0.4rem;
        min-width: 0;
      }
      .dpu-drf__field {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        margin: 0;
        min-width: 0;
      }
      .dpu-drf__caption {
        font-size: 0.7rem;
        font-weight: 600;
        color: var(--dpu-muted);
      }
      .dpu-drf__field ::ng-deep .form-control {
        min-width: 0;
        width: 8.5rem;
        height: 2.4rem;
      }
      .dpu-drf__sep {
        color: var(--dpu-muted);
        padding-bottom: 0.55rem;
      }
      @media (max-width: 639.98px) {
        .dpu-drf__inputs {
          width: 100%;
        }
        .dpu-drf__field {
          flex: 1 1 0;
        }
        .dpu-drf__field ::ng-deep .form-control {
          width: 100%;
        }
      }
    `,
  ],
})
export class DateRangeFilterComponent implements OnInit, OnChanges {
  @Input() value: DateRangeValue | null = null;
  @Input() defaultPreset: DateRangePreset = 'thisMonth';
  @Input() showPresets = true;
  @Output() rangeChange = new EventEmitter<DateRangeValue>();

  readonly presets = DATE_RANGE_PRESETS.filter((p) => p !== 'custom');
  readonly uid = `dpu-drf-${++nextId}`;
  current: DateRangeValue = { from: '', to: '', preset: 'custom' };

  ngOnInit(): void {
    if (!this.value) this.syncFromInput();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['value'] || changes['defaultPreset']) this.syncFromInput();
  }

  selectPreset(preset: DateRangePreset): void {
    const r = resolvePreset(preset);
    if (!r) return;
    this.current = r;
    this.rangeChange.emit({ ...r });
  }

  onDateInput(edge: 'from' | 'to', raw: unknown): void {
    const val = typeof raw === 'string' ? raw.slice(0, 10) : '';
    if (!isIsoDate(val) || val === this.current[edge]) return;
    const next = normalizeRange({ ...this.current, [edge]: val });
    next.preset = detectPreset(next);
    this.current = next;
    this.rangeChange.emit({ ...next });
  }

  private syncFromInput(): void {
    const v = this.value;
    if (v && isIsoDate(v.from) && isIsoDate(v.to)) {
      this.current = {
        from: v.from,
        to: v.to,
        preset: v.preset || detectPreset(v, bangkokToday()),
      };
      return;
    }
    this.current = resolvePreset(this.defaultPreset) || this.current;
  }
}
