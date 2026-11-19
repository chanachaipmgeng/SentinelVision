import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Bento Grid Container (`<app-bento-grid>`).
 * Provides a responsive 12-column CSS Grid with configurable gap and dense auto-flow.
 */
@Component({
  selector: 'app-bento-grid',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="sv-bento-grid"
      [class.sv-bento-grid--dense]="dense"
      [class]="gapClass"
      [ngClass]="extraClass"
      [style.gap]="inlineGap">
      <ng-content></ng-content>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
        width: 100%;
      }
      .sv-bento-grid {
        display: grid;
        grid-template-columns: repeat(12, minmax(0, 1fr));
        width: 100%;
        position: relative;
      }
      .sv-bento-grid--dense {
        grid-auto-flow: dense;
      }
      @media (max-width: 767.98px) {
        .sv-bento-grid {
          grid-template-columns: 1fr !important;
          gap: 0.875rem !important;
        }
        :host ::ng-deep .sv-bento-grid > * {
          grid-column: span 12 / span 12 !important;
        }
      }
    `,
  ],
})
export class BentoGridComponent {
  @Input() gap = '1.25rem';
  @Input() dense = false;
  @Input() extraClass = '';

  get isTailwindGap(): boolean {
    return typeof this.gap === 'string' && this.gap.startsWith('gap-');
  }

  get gapClass(): string {
    return this.isTailwindGap ? this.gap : '';
  }

  get inlineGap(): string {
    return this.isTailwindGap ? '' : this.gap;
  }
}
