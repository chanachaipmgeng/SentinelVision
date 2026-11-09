import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';

export type SkeletonVariant = 'rows' | 'cards' | 'kpi';

@Component({
  selector: 'app-skeleton-loader',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="dpu-skel"
      [ngClass]="'dpu-skel--' + variant"
      role="status"
      aria-live="polite"
      aria-busy="true">
      <span class="dpu-skel__sr">{{ (label || 'listKit.common.loading') | translate }}</span>

      <ng-container [ngSwitch]="variant">
        <ng-container *ngSwitchCase="'cards'">
          <div class="dpu-skel__card" *ngFor="let _ of items" aria-hidden="true">
            <span class="dpu-skel__block dpu-skel__media"></span>
            <span class="dpu-skel__block dpu-skel__line" style="width: 70%"></span>
            <span class="dpu-skel__block dpu-skel__line dpu-skel__line--sm" style="width: 45%"></span>
          </div>
        </ng-container>

        <ng-container *ngSwitchCase="'kpi'">
          <div class="dpu-skel__kpi" *ngFor="let _ of items" aria-hidden="true">
            <span class="dpu-skel__block dpu-skel__icon"></span>
            <span class="dpu-skel__block dpu-skel__line dpu-skel__line--sm" style="width: 55%"></span>
            <span class="dpu-skel__block dpu-skel__value"></span>
          </div>
        </ng-container>

        <ng-container *ngSwitchDefault>
          <div class="dpu-skel__row" *ngFor="let _ of items; let i = index" aria-hidden="true">
            <span *ngIf="avatar" class="dpu-skel__block dpu-skel__avatar"></span>
            <span class="dpu-skel__stack">
              <span class="dpu-skel__block dpu-skel__line" [style.width.%]="rowWidth(i)"></span>
              <span class="dpu-skel__block dpu-skel__line dpu-skel__line--sm" [style.width.%]="rowWidth(i + 3) - 25"></span>
            </span>
            <span class="dpu-skel__block dpu-skel__pill"></span>
          </div>
        </ng-container>
      </ng-container>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }
      .dpu-skel__sr {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip: rect(0 0 0 0);
        white-space: nowrap;
      }
      .dpu-skel--rows {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        padding: 0.75rem;
      }
      .dpu-skel--cards {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
        gap: 0.75rem;
      }
      .dpu-skel--kpi {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
        gap: 0.75rem;
      }
      .dpu-skel__row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.65rem 0.75rem;
        border: 1px solid var(--dpu-border);
        border-radius: var(--dpu-radius-sm);
        background: var(--dpu-surface-elevated);
      }
      .dpu-skel__card,
      .dpu-skel__kpi {
        display: flex;
        flex-direction: column;
        gap: 0.55rem;
        padding: 0.9rem;
        border: 1px solid var(--dpu-border);
        border-radius: var(--dpu-radius);
        background: var(--dpu-surface-elevated);
      }
      .dpu-skel__stack {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
        min-width: 0;
      }
      .dpu-skel__block {
        display: block;
        border-radius: 0.4rem;
        background: linear-gradient(
          90deg,
          var(--dpu-border) 0%,
          var(--dpu-surface) 45%,
          var(--dpu-border) 90%
        );
        background-size: 220% 100%;
        animation: dpu-skel-shimmer 1.3s ease-in-out infinite;
      }
      .dpu-skel__avatar {
        width: 2.6rem;
        height: 2.6rem;
        border-radius: 0.75rem;
        flex-shrink: 0;
      }
      .dpu-skel__line {
        height: 0.8rem;
      }
      .dpu-skel__line--sm {
        height: 0.6rem;
      }
      .dpu-skel__pill {
        width: 3.2rem;
        height: 1.4rem;
        border-radius: 999px;
        flex-shrink: 0;
      }
      .dpu-skel__media {
        height: 7rem;
        border-radius: var(--dpu-radius-sm);
      }
      .dpu-skel__icon {
        width: 2rem;
        height: 2rem;
        border-radius: 0.6rem;
      }
      .dpu-skel__value {
        width: 40%;
        height: 1.5rem;
      }
      @keyframes dpu-skel-shimmer {
        0% {
          background-position: 100% 0;
        }
        100% {
          background-position: -100% 0;
        }
      }
      @media (prefers-reduced-motion: reduce) {
        .dpu-skel__block {
          animation: none;
          background: var(--dpu-border);
        }
      }
    `,
  ],
})
export class SkeletonLoaderComponent {
  @Input() variant: SkeletonVariant = 'rows';
  @Input() count = 5;
  /** Rows variant: show a leading avatar block. */
  @Input() avatar = true;
  /** Screen-reader text (i18n key). */
  @Input() label = '';

  get items(): number[] {
    return Array.from({ length: Math.max(1, Math.min(this.count, 24)) }, (_, i) => i);
  }

  rowWidth(i: number): number {
    return [78, 64, 86, 70, 58, 82][i % 6];
  }
}
