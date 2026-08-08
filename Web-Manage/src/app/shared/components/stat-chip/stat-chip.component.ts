import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type StatChipTone = 'default' | 'ok' | 'warn' | 'danger' | 'soft' | 'temp';

@Component({
  selector: 'app-stat-chip',
  standalone: true,
  imports: [CommonModule],
  template: `<span class="dpu-stat-chip" [attr.data-tone]="tone"><ng-content></ng-content></span>`,
  styles: [
    `
      :host {
        display: inline-flex;
      }
      .dpu-stat-chip {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 600;
        color: var(--dpu-brand-deep, #0b4f4a);
        background: rgba(15, 118, 110, 0.12);
      }
      .dpu-stat-chip[data-tone='ok'] {
        color: #166534;
        background: rgba(22, 163, 74, 0.14);
      }
      .dpu-stat-chip[data-tone='warn'],
      .dpu-stat-chip[data-tone='temp'] {
        color: #9a3412;
        background: rgba(234, 88, 12, 0.14);
      }
      .dpu-stat-chip[data-tone='danger'] {
        color: #991b1b;
        background: rgba(220, 38, 38, 0.12);
      }
      .dpu-stat-chip[data-tone='soft'] {
        color: var(--dpu-muted, #64748b);
        background: rgba(100, 116, 139, 0.12);
      }
    `,
  ],
})
export class StatChipComponent {
  @Input() tone: StatChipTone = 'default';
}
