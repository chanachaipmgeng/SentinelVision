import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';

export type BentoAccentTone = 'cyan' | 'sky' | 'rose' | 'amber' | 'violet' | 'emerald' | 'slate';

/**
 * Bento Card Component (`<app-bento-card>`).
 * VaultX Obsidian Glass card wrapper with rim gradient, optional hover glow,
 * responsive col/row spans, and slots for headerExtra, content, and footer.
 */
@Component({
  selector: 'app-bento-card',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  template: `
    <div
      class="sv-bento-card card-surface"
      [ngClass]="[colSpan, rowSpan, 'accent-' + accentTone]"
      [attr.data-tone]="accentTone"
      [class.is-clickable]="clickable"
      [class.is-compact]="compact"
      [class.has-hover-glow]="hoverGlow"
      (click)="onClick($event)">
      <!-- Top Accent Line Indicator -->
      <div class="sv-bento-card__accent-line" [attr.data-tone]="accentTone" aria-hidden="true"></div>

      <!-- Card Header -->
      <header class="sv-bento-card__header" *ngIf="title || effectiveIcon">
        <div class="sv-bento-card__title-group">
          <div class="sv-bento-card__icon" *ngIf="effectiveIcon" [attr.data-tone]="accentTone">
            <i [ngClass]="effectiveIcon" aria-hidden="true"></i>
          </div>
          <div class="sv-bento-card__titles">
            <div class="sv-bento-card__title">
              <span class="sv-bento-card__title-text">{{ title | translate }}</span>
              <span
                *ngIf="badge"
                class="sv-bento-card__badge"
                [attr.data-tone]="badgeTone || accentTone">
                {{ badge | translate }}
              </span>
            </div>
            <p class="sv-bento-card__subtitle" *ngIf="subtitle">
              {{ subtitle | translate }}
            </p>
          </div>
        </div>
        <div class="sv-bento-card__header-extra">
          <ng-content select="[headerExtra]"></ng-content>
        </div>
      </header>

      <!-- Card Body Content Slot -->
      <div class="sv-bento-card__body">
        <ng-content></ng-content>
      </div>

      <!-- Card Footer Slot -->
      <footer class="sv-bento-card__footer">
        <ng-content select="[footer]"></ng-content>
      </footer>
    </div>
  `,
  styles: [
    `
      :host {
        display: contents;
      }

      .sv-bento-card {
        position: relative;
        display: flex;
        flex-direction: column;
        border-radius: 18px;
        padding: 1.25rem 1.35rem;
        background: linear-gradient(180deg, #070d14, #03060a) padding-box,
          linear-gradient(180deg, rgba(255, 255, 255, 0.14), rgba(255, 255, 255, 0.03) 40%, transparent 80%) border-box;
        border: 1px solid transparent;
        transition: transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1),
          box-shadow 0.25s cubic-bezier(0.2, 0.8, 0.2, 1),
          border-color 0.25s ease;
        overflow: hidden;
      }

      .sv-bento-card.is-compact {
        padding: 0.95rem 1.05rem;
      }

      .sv-bento-card.is-clickable {
        cursor: pointer;
      }

      /* Subtle top rim glow bar */
      .sv-bento-card__accent-line {
        position: absolute;
        top: 0;
        left: 1.5rem;
        right: 1.5rem;
        height: 2px;
        opacity: 0.85;
        border-radius: 9999px;
        transition: opacity 0.25s ease;
      }

      .sv-bento-card__accent-line[data-tone='cyan'] {
        background: linear-gradient(90deg, transparent, #06b6d4, transparent);
      }
      .sv-bento-card__accent-line[data-tone='sky'] {
        background: linear-gradient(90deg, transparent, #0284c7, transparent);
      }
      .sv-bento-card__accent-line[data-tone='rose'] {
        background: linear-gradient(90deg, transparent, #f43f5e, transparent);
      }
      .sv-bento-card__accent-line[data-tone='amber'] {
        background: linear-gradient(90deg, transparent, #f59e0b, transparent);
      }
      .sv-bento-card__accent-line[data-tone='violet'] {
        background: linear-gradient(90deg, transparent, #8b5cf6, transparent);
      }
      .sv-bento-card__accent-line[data-tone='emerald'] {
        background: linear-gradient(90deg, transparent, #10b981, transparent);
      }
      .sv-bento-card__accent-line[data-tone='slate'] {
        background: linear-gradient(90deg, transparent, #94a3b8, transparent);
      }

      /* Hover Glow Tones */
      .sv-bento-card.has-hover-glow:hover {
        transform: translateY(-2px);
      }

      .sv-bento-card.has-hover-glow[data-tone='cyan']:hover {
        box-shadow: 0 12px 32px -4px rgba(6, 182, 212, 0.22);
        border-color: rgba(6, 182, 212, 0.4);
      }
      .sv-bento-card.has-hover-glow[data-tone='sky']:hover {
        box-shadow: 0 12px 32px -4px rgba(2, 132, 199, 0.22);
        border-color: rgba(2, 132, 199, 0.4);
      }
      .sv-bento-card.has-hover-glow[data-tone='rose']:hover {
        box-shadow: 0 12px 32px -4px rgba(244, 63, 94, 0.22);
        border-color: rgba(244, 63, 94, 0.4);
      }
      .sv-bento-card.has-hover-glow[data-tone='amber']:hover {
        box-shadow: 0 12px 32px -4px rgba(245, 158, 11, 0.22);
        border-color: rgba(245, 158, 11, 0.4);
      }
      .sv-bento-card.has-hover-glow[data-tone='violet']:hover {
        box-shadow: 0 12px 32px -4px rgba(139, 92, 246, 0.22);
        border-color: rgba(139, 92, 246, 0.4);
      }
      .sv-bento-card.has-hover-glow[data-tone='emerald']:hover {
        box-shadow: 0 12px 32px -4px rgba(16, 185, 129, 0.22);
        border-color: rgba(16, 185, 129, 0.4);
      }
      .sv-bento-card.has-hover-glow[data-tone='slate']:hover {
        box-shadow: 0 12px 32px -4px rgba(148, 163, 184, 0.18);
        border-color: rgba(148, 163, 184, 0.35);
      }

      /* Card Header */
      .sv-bento-card__header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 0.75rem;
        margin-bottom: 0.85rem;
      }

      .sv-bento-card__title-group {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex: 1 1 auto;
        min-width: 0;
      }

      .sv-bento-card__icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 2.25rem;
        height: 2.25rem;
        border-radius: 10px;
        font-size: 1.15rem;
        flex-shrink: 0;
      }

      .sv-bento-card__icon[data-tone='cyan'] {
        background: rgba(6, 182, 212, 0.14);
        color: #38bdf8;
        border: 1px solid rgba(6, 182, 212, 0.25);
      }
      .sv-bento-card__icon[data-tone='sky'] {
        background: rgba(2, 132, 199, 0.14);
        color: #38bdf8;
        border: 1px solid rgba(2, 132, 199, 0.25);
      }
      .sv-bento-card__icon[data-tone='rose'] {
        background: rgba(244, 63, 94, 0.14);
        color: #fb7185;
        border: 1px solid rgba(244, 63, 94, 0.25);
      }
      .sv-bento-card__icon[data-tone='amber'] {
        background: rgba(245, 158, 11, 0.14);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.25);
      }
      .sv-bento-card__icon[data-tone='violet'] {
        background: rgba(139, 92, 246, 0.14);
        color: #c084fc;
        border: 1px solid rgba(139, 92, 246, 0.25);
      }
      .sv-bento-card__icon[data-tone='emerald'] {
        background: rgba(16, 185, 129, 0.14);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.25);
      }
      .sv-bento-card__icon[data-tone='slate'] {
        background: rgba(148, 163, 184, 0.14);
        color: #cbd5e1;
        border: 1px solid rgba(148, 163, 184, 0.25);
      }

      .sv-bento-card__titles {
        display: flex;
        flex-direction: column;
        min-width: 0;
      }

      .sv-bento-card__title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
      }

      .sv-bento-card__title-text {
        font-size: 0.9375rem;
        font-weight: 700;
        color: #f1f5f9;
        letter-spacing: -0.01em;
      }

      .sv-bento-card__badge {
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        padding: 0.15rem 0.45rem;
        border-radius: 9999px;
        letter-spacing: 0.04em;
      }

      .sv-bento-card__badge[data-tone='cyan'] {
        background: rgba(6, 182, 212, 0.18);
        color: #67e8f9;
        border: 1px solid rgba(6, 182, 212, 0.35);
      }
      .sv-bento-card__badge[data-tone='sky'] {
        background: rgba(2, 132, 199, 0.18);
        color: #7dd3fc;
        border: 1px solid rgba(2, 132, 199, 0.35);
      }
      .sv-bento-card__badge[data-tone='rose'] {
        background: rgba(244, 63, 94, 0.18);
        color: #fda4af;
        border: 1px solid rgba(244, 63, 94, 0.35);
      }
      .sv-bento-card__badge[data-tone='amber'] {
        background: rgba(245, 158, 11, 0.18);
        color: #fde68a;
        border: 1px solid rgba(245, 158, 11, 0.35);
      }
      .sv-bento-card__badge[data-tone='violet'] {
        background: rgba(139, 92, 246, 0.18);
        color: #d8b4fe;
        border: 1px solid rgba(139, 92, 246, 0.35);
      }
      .sv-bento-card__badge[data-tone='emerald'] {
        background: rgba(16, 185, 129, 0.18);
        color: #6ee7b7;
        border: 1px solid rgba(16, 185, 129, 0.35);
      }
      .sv-bento-card__badge[data-tone='slate'] {
        background: rgba(148, 163, 184, 0.18);
        color: #e2e8f0;
        border: 1px solid rgba(148, 163, 184, 0.35);
      }

      .sv-bento-card__subtitle {
        font-size: 0.75rem;
        color: #94a3b8;
        margin: 0.15rem 0 0;
        line-height: 1.3;
      }

      .sv-bento-card__header-extra {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        flex-shrink: 0;
      }

      .sv-bento-card__body {
        flex: 1 1 auto;
        display: flex;
        flex-direction: column;
        color: #cbd5e1;
      }

      .sv-bento-card__footer {
        margin-top: 0.85rem;
        padding-top: 0.65rem;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .sv-bento-card__footer:empty {
        display: none;
      }

      /* Light Theme Overrides */
      html[data-theme-mode='light'] .sv-bento-card,
      html[data-theme='light'] .sv-bento-card,
      html:not(.dark) .sv-bento-card {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
      }

      html[data-theme-mode='light'] .sv-bento-card__title-text,
      html[data-theme='light'] .sv-bento-card__title-text,
      html:not(.dark) .sv-bento-card__title-text {
        color: #0f172a !important;
      }

      html[data-theme-mode='light'] .sv-bento-card__subtitle,
      html[data-theme='light'] .sv-bento-card__subtitle,
      html:not(.dark) .sv-bento-card__subtitle {
        color: #64748b !important;
      }

      html[data-theme-mode='light'] .sv-bento-card__body,
      html[data-theme='light'] .sv-bento-card__body,
      html:not(.dark) .sv-bento-card__body {
        color: #334155 !important;
      }

      html[data-theme-mode='light'] .sv-bento-card__footer,
      html[data-theme='light'] .sv-bento-card__footer,
      html:not(.dark) .sv-bento-card__footer {
        border-top-color: #f1f5f9 !important;
      }
    `,
  ],
})
export class BentoCardComponent {
  @Input() colSpan = 'col-span-12 lg:col-span-6';
  @Input() rowSpan = '';
  @Input() accentTone: BentoAccentTone = 'cyan';
  @Input() hoverGlow = true;
  @Input() title = '';
  @Input() subtitle = '';
  @Input() icon = '';
  @Input() headerIcon = '';
  @Input() badge = '';
  @Input() badgeTone = '';
  @Input() clickable = false;
  @Input() compact = false;

  @Output() cardClick = new EventEmitter<MouseEvent>();

  get effectiveIcon(): string {
    return this.icon || this.headerIcon;
  }

  onClick(event: MouseEvent): void {
    if (this.clickable) {
      this.cardClick.emit(event);
    }
  }
}
