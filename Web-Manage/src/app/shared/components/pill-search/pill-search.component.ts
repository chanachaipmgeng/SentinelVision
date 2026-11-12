import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
    selector: 'app-pill-search',
    imports: [CommonModule, FormsModule],
    template: `
    <div class="dpu-pill-search">
      <i class="ri-search-line dpu-pill-search__icon" aria-hidden="true"></i>
      <input
        class="form-control dpu-pill-search__input"
        type="search"
        [ngModel]="value"
        (ngModelChange)="onChange($event)"
        [placeholder]="placeholder"
        [attr.aria-label]="ariaLabel || placeholder">
      <button
        *ngIf="value"
        type="button"
        class="dpu-pill-search__clear"
        title="ล้างคำค้น"
        (click)="clear()">
        <i class="ri-close-line"></i>
      </button>
    </div>
  `,
    styles: [
        `
      :host {
        display: block;
        flex: 1 1 12rem;
        min-width: 11rem;
        max-width: 26rem;
      }
      @media (max-width: 767.98px) {
        :host {
          flex: 1 1 100%;
          min-width: 0;
          max-width: none;
        }
      }
      .dpu-pill-search {
        position: relative;
        width: 100%;
      }
      .dpu-pill-search__icon {
        position: absolute;
        left: 0.8rem;
        top: 50%;
        transform: translateY(-50%);
        color: var(--dpu-muted, #64748b);
        pointer-events: none;
        z-index: 1;
      }
      .dpu-pill-search__input {
        width: 100% !important;
        height: 2.4rem !important;
        padding: 0.45rem 2.2rem 0.45rem 2.25rem !important;
        border-radius: 999px !important;
        border: 1px solid var(--dpu-border, #e2e8f0) !important;
        background: var(--dpu-surface-elevated, #fff) !important;
        color: var(--dpu-ink, #0f172a) !important;
      }
      .dpu-pill-search__input:focus {
        border-color: var(--dpu-brand, #0f766e) !important;
        box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.14) !important;
        outline: none;
      }
      .dpu-pill-search__clear {
        position: absolute;
        right: 0.35rem;
        top: 50%;
        transform: translateY(-50%);
        width: 1.75rem;
        height: 1.75rem;
        border: 0;
        border-radius: 999px;
        background: transparent;
        color: var(--dpu-muted, #64748b);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
      }
      .dpu-pill-search__clear:hover {
        background: rgba(100, 116, 139, 0.12);
      }
    `,
    ]
})
export class PillSearchComponent {
  @Input() value = '';
  @Input() placeholder = 'ค้นหา...';
  @Input() ariaLabel = '';
  @Output() valueChange = new EventEmitter<string>();

  onChange(val: string) {
    this.value = val;
    this.valueChange.emit(val);
  }

  clear() {
    this.onChange('');
  }
}
