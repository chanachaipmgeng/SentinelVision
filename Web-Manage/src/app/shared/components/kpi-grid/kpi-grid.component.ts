import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { SkeletonLoaderComponent } from '../skeleton-loader/skeleton-loader.component';

export type KpiTone = 'brand' | 'success' | 'warning' | 'danger' | 'muted';
export type KpiTrend = 'up' | 'down' | 'flat';

export interface KpiItem {
  /** Stable id; also what `tileClick` emits. */
  key: string;
  /** Text or i18n key. */
  label: string;
  value: string | number;
  icon?: string;
  tone?: KpiTone;
  /** e.g. `+12%` or `-3`; shown next to the trend arrow. */
  delta?: string | number;
  trend?: KpiTrend;
  /** Whether "up" is good (green) — set false for metrics like late count. */
  upIsGood?: boolean;
  /** Secondary caption (text or i18n key). */
  hint?: string;
}

@Component({
  selector: 'app-kpi-grid',
  standalone: true,
  imports: [CommonModule, TranslateModule, SkeletonLoaderComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-skeleton-loader *ngIf="loading; else grid" variant="kpi" [count]="items.length || 4"></app-skeleton-loader>
    <ng-template #grid>
      <ul class="dpu-kpi" [style.--dpu-kpi-min]="minTileWidth">
        <li *ngFor="let k of items; trackBy: trackByKey">
          <button
            *ngIf="clickable; else staticTile"
            type="button"
            class="dpu-kpi__tile is-clickable"
            [attr.data-tone]="k.tone || 'brand'"
            [class.is-selected]="k.key === selectedKey"
            [attr.aria-pressed]="k.key === selectedKey"
            (click)="tileClick.emit(k.key)">
            <ng-container *ngTemplateOutlet="body; context: { $implicit: k }"></ng-container>
          </button>
          <ng-template #staticTile>
            <div class="dpu-kpi__tile" [attr.data-tone]="k.tone || 'brand'">
              <ng-container *ngTemplateOutlet="body; context: { $implicit: k }"></ng-container>
            </div>
          </ng-template>
        </li>
      </ul>
    </ng-template>

    <ng-template #body let-k>
      <span class="dpu-kpi__icon" *ngIf="k.icon" aria-hidden="true"><i [ngClass]="k.icon"></i></span>
      <span class="dpu-kpi__text">
        <span class="dpu-kpi__label">{{ k.label | translate }}</span>
        <span class="dpu-kpi__value">{{ k.value }}</span>
        <span class="dpu-kpi__meta" *ngIf="k.delta != null || k.hint">
          <span
            *ngIf="k.delta != null"
            class="dpu-kpi__delta"
            [attr.data-good]="isGood(k)">
            <i [ngClass]="trendIcon(k)" aria-hidden="true"></i>{{ k.delta }}
          </span>
          <span class="dpu-kpi__hint" *ngIf="k.hint">{{ k.hint | translate }}</span>
        </span>
      </span>
    </ng-template>
  `,
  styles: [
    `
      :host {
        display: block;
      }
      .dpu-kpi {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(var(--dpu-kpi-min, 10.5rem), 1fr));
        gap: 0.75rem;
      }
      .dpu-kpi__tile {
        --tone: var(--dpu-brand);
        width: 100%;
        height: 100%;
        display: flex;
        align-items: flex-start;
        gap: 0.7rem;
        padding: 0.85rem 0.95rem;
        text-align: start;
        border: 1px solid var(--dpu-border);
        border-radius: var(--dpu-radius);
        background: var(--dpu-surface-elevated);
        box-shadow: var(--dpu-shadow);
        color: var(--dpu-ink);
        font: inherit;
      }
      .dpu-kpi__tile[data-tone='success'] {
        --tone: var(--dpu-success);
      }
      .dpu-kpi__tile[data-tone='warning'] {
        --tone: var(--dpu-warning);
      }
      .dpu-kpi__tile[data-tone='danger'] {
        --tone: var(--dpu-danger);
      }
      .dpu-kpi__tile[data-tone='muted'] {
        --tone: var(--dpu-muted);
      }
      .dpu-kpi__tile.is-clickable {
        cursor: pointer;
        transition: border-color var(--dpu-duration) var(--dpu-ease),
          transform var(--dpu-duration) var(--dpu-ease);
      }
      .dpu-kpi__tile.is-clickable:hover {
        border-color: var(--tone);
        transform: translateY(-1px);
      }
      .dpu-kpi__tile.is-clickable:focus-visible {
        outline: 2px solid var(--tone);
        outline-offset: 2px;
      }
      .dpu-kpi__tile.is-selected {
        border-color: var(--tone);
        box-shadow: inset 0 0 0 1px var(--tone);
      }
      .dpu-kpi__icon {
        flex-shrink: 0;
        width: 2.2rem;
        height: 2.2rem;
        border-radius: 0.7rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        color: var(--tone);
        background: color-mix(in srgb, var(--tone) 12%, transparent);
      }
      .dpu-kpi__text {
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
        min-width: 0;
      }
      .dpu-kpi__label {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--dpu-muted);
      }
      .dpu-kpi__value {
        font-family: var(--dpu-font-display);
        font-size: 1.35rem;
        font-weight: 800;
        line-height: 1.2;
        color: var(--dpu-ink);
      }
      .dpu-kpi__meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        font-size: 0.72rem;
      }
      .dpu-kpi__delta {
        display: inline-flex;
        align-items: center;
        gap: 0.1rem;
        font-weight: 700;
        color: var(--dpu-muted);
      }
      .dpu-kpi__delta[data-good='true'] {
        color: var(--dpu-success);
      }
      .dpu-kpi__delta[data-good='false'] {
        color: var(--dpu-danger);
      }
      .dpu-kpi__hint {
        color: var(--dpu-muted);
      }
      @media (prefers-reduced-motion: reduce) {
        .dpu-kpi__tile.is-clickable {
          transition: none;
        }
        .dpu-kpi__tile.is-clickable:hover {
          transform: none;
        }
      }
    `,
  ],
})
export class KpiGridComponent {
  @Input() items: KpiItem[] = [];
  @Input() loading = false;
  /** Render tiles as buttons and emit `tileClick` (e.g. quick filters). */
  @Input() clickable = false;
  @Input() selectedKey: string | null = null;
  @Input() minTileWidth = '10.5rem';
  @Output() tileClick = new EventEmitter<string>();

  trackByKey(_: number, k: KpiItem): string {
    return k.key;
  }

  trendIcon(k: KpiItem): string {
    if (k.trend === 'up') return 'ri-arrow-up-line';
    if (k.trend === 'down') return 'ri-arrow-down-line';
    return 'ri-subtract-line';
  }

  /** `null` (neutral) for flat/unknown trends; rendered as a data attribute. */
  isGood(k: KpiItem): boolean | null {
    if (!k.trend || k.trend === 'flat') return null;
    const upGood = k.upIsGood !== false;
    return k.trend === 'up' ? upGood : !upGood;
  }
}
