import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

/**
 * Reusable unified multi-segment KPI ribbon with dashed separators and Dark/Light parity.
 */
@Component({
  selector: 'app-metric-ribbon',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="sv-metric-ribbon sv-surface-ribbon sv-motion-enter sv-stagger-1 grid rounded-2xl overflow-hidden shadow-lg"
      [ngClass]="gridClass"
    >
      <ng-content></ng-content>
    </div>
  `,
})
export class MetricRibbonComponent {
  @Input() columns: 4 | 5 | 6 = 6;

  get gridClass(): string {
    if (this.columns === 4) {
      return 'grid-cols-2 lg:grid-cols-4';
    }
    if (this.columns === 5) {
      return 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-5';
    }
    return 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-6';
  }
}
