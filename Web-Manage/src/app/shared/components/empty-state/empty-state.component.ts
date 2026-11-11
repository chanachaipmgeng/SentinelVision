import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';

@Component({
    selector: 'app-empty-state',
    imports: [CommonModule, TranslateModule],
    template: `
    <div class="dpu-empty">
      <span *ngIf="loading" class="ti-spinner animation-spin dpu-empty__spinner" role="status"></span>
      <i *ngIf="!loading" class="dpu-empty__icon" [ngClass]="icon"></i>
      <p>{{ message | translate }}</p>
      <button
        *ngIf="actionLabel"
        type="button"
        class="ti-btn ti-btn-light modern-btn"
        (click)="action.emit()">
        {{ actionLabel | translate }}
      </button>
    </div>
  `,
    styles: [
        `
      :host {
        display: block;
      }
      .dpu-empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.55rem;
        text-align: center;
        color: var(--dpu-muted, #64748b);
        padding: 3rem 1rem;
      }
      .dpu-empty p {
        margin: 0;
        max-width: 18rem;
      }
      .dpu-empty__icon {
        font-size: 2.4rem;
        color: var(--dpu-brand, #0f766e);
        opacity: 0.7;
      }
      .dpu-empty__spinner {
        width: 1.75rem;
        height: 1.75rem;
      }
    `,
    ]
})
export class EmptyStateComponent {
  @Input() loading = false;
  @Input() message = 'ไม่มีข้อมูล';
  @Input() icon = 'ri-inbox-line';
  @Input() actionLabel = '';
  @Output() action = new EventEmitter<void>();
}
