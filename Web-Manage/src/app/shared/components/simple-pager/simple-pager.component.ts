import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-simple-pager',
    imports: [CommonModule],
    template: `
    <div class="dpu-pager" *ngIf="total > pageSize">
      <button type="button" class="dpu-pager__btn" [disabled]="pageIndex <= 0" (click)="go(pageIndex - 1)">
        <i class="ri-arrow-left-s-line"></i>
      </button>
      <span class="dpu-pager__label">
        แสดง {{ from }}–{{ to }} จาก {{ total }} · หน้า {{ pageIndex + 1 }} / {{ totalPages }}
      </span>
      <button
        type="button"
        class="dpu-pager__btn"
        [disabled]="pageIndex >= totalPages - 1"
        (click)="go(pageIndex + 1)">
        <i class="ri-arrow-right-s-line"></i>
      </button>
    </div>
  `,
    styles: [
        `
      :host {
        display: block;
      }
      .dpu-pager {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        padding: 0.65rem 1rem;
        border-top: 1px solid var(--dpu-border, #e2e8f0);
      }
      .dpu-pager__btn {
        width: 2rem;
        height: 2rem;
        border-radius: 999px;
        border: 1px solid var(--dpu-border, #e2e8f0);
        background: #fff;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
      }
      .dpu-pager__btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
      .dpu-pager__label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #0f172a;
      }
    `,
    ]
})
export class SimplePagerComponent {
  @Input() pageIndex = 0;
  @Input() pageSize = 10;
  @Input() total = 0;
  @Output() pageIndexChange = new EventEmitter<number>();

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.total / this.pageSize));
  }

  get from(): number {
    if (!this.total) return 0;
    return this.pageIndex * this.pageSize + 1;
  }

  get to(): number {
    return Math.min((this.pageIndex + 1) * this.pageSize, this.total);
  }

  go(page: number) {
    const next = Math.max(0, Math.min(page, this.totalPages - 1));
    if (next === this.pageIndex) return;
    this.pageIndexChange.emit(next);
  }
}
