import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Params, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { BentoAccentTone } from './bento-card.component';

/**
 * Bento Stat / KPI Card (`<app-bento-stat>`).
 * Compact, high-visibility metric tile with icon glow, large value, and optional trend/link.
 */
@Component({
  selector: 'app-bento-stat',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslateModule],
  template: `
    <ng-container *ngIf="effectiveLink; else divWrapper">
      <a
        [routerLink]="effectiveLink"
        [queryParams]="queryParams"
        class="sv-bento-stat card-surface"
        [ngClass]="[colSpan, 'accent-' + accentTone]"
        [attr.data-tone]="accentTone">
        <ng-container *ngTemplateOutlet="statContent"></ng-container>
      </a>
    </ng-container>

    <ng-template #divWrapper>
      <div
        class="sv-bento-stat card-surface"
        [ngClass]="[colSpan, 'accent-' + accentTone]"
        [attr.data-tone]="accentTone">
        <ng-container *ngTemplateOutlet="statContent"></ng-container>
      </div>
    </ng-template>

    <ng-template #statContent>
      <div class="sv-bento-stat__head">
        <span class="sv-bento-stat__label">{{ label | translate }}</span>
        <div class="sv-bento-stat__icon" [attr.data-tone]="accentTone">
          <i [ngClass]="icon" aria-hidden="true"></i>
        </div>
      </div>
      <div class="sv-bento-stat__value-wrap flex items-baseline gap-1.5">
        <div class="sv-bento-stat__value" [attr.data-tone]="accentTone">
          {{ value }}
        </div>
        <span *ngIf="unit" class="sv-bento-stat__unit text-xs text-slate-400 font-medium">
          {{ unit | translate }}
        </span>
      </div>
      <div class="sv-bento-stat__meta" *ngIf="effectiveTrendText || subText || badge">
        <span
          *ngIf="effectiveTrendText"
          class="sv-bento-stat__trend"
          [class.is-pos]="isPositiveTrend"
          [class.is-neg]="!isPositiveTrend"
          [class.is-up]="isPositiveTrend"
          [class.is-down]="!isPositiveTrend">
          <i
            [ngClass]="isPositiveTrend ? 'ri-arrow-up-line' : 'ri-arrow-down-line'"
            aria-hidden="true"></i>
          {{ effectiveTrendText | translate }}
        </span>
        <span *ngIf="subText" class="sv-bento-stat__subtext">
          {{ subText | translate }}
        </span>
        <span
          *ngIf="badge"
          class="sv-bento-stat__badge"
          [attr.data-tone]="accentTone">
          {{ badge | translate }}
        </span>
      </div>
    </ng-template>
  `,
  styles: [
    `
      :host {
        display: contents;
      }

      .sv-bento-stat {
        position: relative;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 8.75rem;
        border-radius: 18px;
        padding: 1.15rem 1.25rem;
        background: linear-gradient(180deg, #070d14, #03060a) padding-box,
          linear-gradient(180deg, rgba(255, 255, 255, 0.14), rgba(255, 255, 255, 0.03) 40%, transparent 80%) border-box;
        border: 1px solid transparent;
        transition: transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1),
          box-shadow 0.25s cubic-bezier(0.2, 0.8, 0.2, 1),
          border-color 0.25s ease;
        text-decoration: none;
      }

      a.sv-bento-stat {
        cursor: pointer;
      }

      .sv-bento-stat:hover {
        transform: translateY(-2px);
      }

      .sv-bento-stat[data-tone='cyan']:hover {
        box-shadow: 0 10px 28px -4px rgba(6, 182, 212, 0.25);
        border-color: rgba(6, 182, 212, 0.45);
      }
      .sv-bento-stat[data-tone='sky']:hover {
        box-shadow: 0 10px 28px -4px rgba(2, 132, 199, 0.25);
        border-color: rgba(2, 132, 199, 0.45);
      }
      .sv-bento-stat[data-tone='rose']:hover {
        box-shadow: 0 10px 28px -4px rgba(244, 63, 94, 0.25);
        border-color: rgba(244, 63, 94, 0.45);
      }
      .sv-bento-stat[data-tone='amber']:hover {
        box-shadow: 0 10px 28px -4px rgba(245, 158, 11, 0.25);
        border-color: rgba(245, 158, 11, 0.45);
      }
      .sv-bento-stat[data-tone='violet']:hover {
        box-shadow: 0 10px 28px -4px rgba(139, 92, 246, 0.25);
        border-color: rgba(139, 92, 246, 0.45);
      }
      .sv-bento-stat[data-tone='emerald']:hover {
        box-shadow: 0 10px 28px -4px rgba(16, 185, 129, 0.25);
        border-color: rgba(16, 185, 129, 0.45);
      }
      .sv-bento-stat[data-tone='slate']:hover {
        box-shadow: 0 10px 28px -4px rgba(148, 163, 184, 0.2);
        border-color: rgba(148, 163, 184, 0.35);
      }

      .sv-bento-stat__head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
      }

      .sv-bento-stat__label {
        font-size: 0.8125rem;
        font-weight: 600;
        color: #94a3b8;
        letter-spacing: -0.01em;
      }

      .sv-bento-stat__icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 2.1rem;
        height: 2.1rem;
        border-radius: 10px;
        font-size: 1.1rem;
      }

      .sv-bento-stat__icon[data-tone='cyan'] {
        background: rgba(6, 182, 212, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(6, 182, 212, 0.25);
      }
      .sv-bento-stat__icon[data-tone='sky'] {
        background: rgba(2, 132, 199, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(2, 132, 199, 0.25);
      }
      .sv-bento-stat__icon[data-tone='rose'] {
        background: rgba(244, 63, 94, 0.12);
        color: #fb7185;
        border: 1px solid rgba(244, 63, 94, 0.25);
      }
      .sv-bento-stat__icon[data-tone='amber'] {
        background: rgba(245, 158, 11, 0.12);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.25);
      }
      .sv-bento-stat__icon[data-tone='violet'] {
        background: rgba(139, 92, 246, 0.12);
        color: #c084fc;
        border: 1px solid rgba(139, 92, 246, 0.25);
      }
      .sv-bento-stat__icon[data-tone='emerald'] {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.25);
      }
      .sv-bento-stat__icon[data-tone='slate'] {
        background: rgba(148, 163, 184, 0.12);
        color: #cbd5e1;
        border: 1px solid rgba(148, 163, 184, 0.25);
      }

      .sv-bento-stat__value {
        font-size: 1.875rem;
        font-weight: 800;
        line-height: 1.2;
        letter-spacing: -0.02em;
        margin: 0.35rem 0 0.2rem;
      }

      .sv-bento-stat__value[data-tone='cyan'] {
        color: #22d3ee;
      }
      .sv-bento-stat__value[data-tone='sky'] {
        color: #38bdf8;
      }
      .sv-bento-stat__value[data-tone='rose'] {
        color: #fb7185;
      }
      .sv-bento-stat__value[data-tone='amber'] {
        color: #fbbf24;
      }
      .sv-bento-stat__value[data-tone='violet'] {
        color: #c084fc;
      }
      .sv-bento-stat__value[data-tone='emerald'] {
        color: #34d399;
      }
      .sv-bento-stat__value[data-tone='slate'] {
        color: #f1f5f9;
      }

      .sv-bento-stat__meta {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.72rem;
        flex-wrap: wrap;
      }

      .sv-bento-stat__trend {
        display: inline-flex;
        align-items: center;
        gap: 0.15rem;
        font-weight: 600;
      }

      .sv-bento-stat__trend.is-pos {
        color: #34d399;
      }
      .sv-bento-stat__trend.is-neg {
        color: #fb7185;
      }

      .sv-bento-stat__subtext {
        color: #64748b;
      }

      .sv-bento-stat__badge {
        font-size: 0.65rem;
        font-weight: 700;
        padding: 0.1rem 0.4rem;
        border-radius: 9999px;
      }

      /* Light Mode */
      html[data-theme-mode='light'] .sv-bento-stat,
      html[data-theme='light'] .sv-bento-stat,
      html:not(.dark) .sv-bento-stat {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
      }

      html[data-theme-mode='light'] .sv-bento-stat__label,
      html[data-theme='light'] .sv-bento-stat__label,
      html:not(.dark) .sv-bento-stat__label {
        color: #64748b !important;
      }

      html[data-theme-mode='light'] .sv-bento-stat__value[data-tone='cyan'],
      html[data-theme='light'] .sv-bento-stat__value[data-tone='cyan'],
      html:not(.dark) .sv-bento-stat__value[data-tone='cyan'] {
        color: #0891b2 !important;
      }

      html[data-theme-mode='light'] .sv-bento-stat__value[data-tone='sky'],
      html[data-theme='light'] .sv-bento-stat__value[data-tone='sky'],
      html:not(.dark) .sv-bento-stat__value[data-tone='sky'] {
        color: #0284c7 !important;
      }

      html[data-theme-mode='light'] .sv-bento-stat__value[data-tone='rose'],
      html[data-theme='light'] .sv-bento-stat__value[data-tone='rose'],
      html:not(.dark) .sv-bento-stat__value[data-tone='rose'] {
        color: #e11d48 !important;
      }

      html[data-theme-mode='light'] .sv-bento-stat__value[data-tone='amber'],
      html[data-theme='light'] .sv-bento-stat__value[data-tone='amber'],
      html:not(.dark) .sv-bento-stat__value[data-tone='amber'] {
        color: #d97706 !important;
      }

      html[data-theme-mode='light'] .sv-bento-stat__value[data-tone='violet'],
      html[data-theme='light'] .sv-bento-stat__value[data-tone='violet'],
      html:not(.dark) .sv-bento-stat__value[data-tone='violet'] {
        color: #7c3aed !important;
      }

      html[data-theme-mode='light'] .sv-bento-stat__value[data-tone='emerald'],
      html[data-theme='light'] .sv-bento-stat__value[data-tone='emerald'],
      html:not(.dark) .sv-bento-stat__value[data-tone='emerald'] {
        color: #059669 !important;
      }

      html[data-theme-mode='light'] .sv-bento-stat__value[data-tone='slate'],
      html[data-theme='light'] .sv-bento-stat__value[data-tone='slate'],
      html:not(.dark) .sv-bento-stat__value[data-tone='slate'] {
        color: #0f172a !important;
      }
    `,
  ],
})
export class BentoStatComponent {
  @Input() colSpan = 'col-span-12 sm:col-span-6 xl:col-span-3';
  @Input() label = '';
  @Input() value: string | number = '';
  @Input() unit = '';
  @Input() icon = '';
  @Input() accentTone: BentoAccentTone = 'cyan';
  @Input() trendText = '';
  @Input() trendLabel = '';
  @Input() trend: 'up' | 'down' | '' = '';
  @Input() trendPositive = true;
  @Input() link = '';
  @Input() routerLink = '';
  @Input() queryParams: Params = {};
  @Input() subText = '';
  @Input() badge = '';

  get effectiveLink(): string {
    return this.link || this.routerLink;
  }

  get effectiveTrendText(): string {
    return this.trendText || this.trendLabel;
  }

  get isPositiveTrend(): boolean {
    if (this.trend === 'up') return true;
    if (this.trend === 'down') return false;
    return this.trendPositive;
  }
}
