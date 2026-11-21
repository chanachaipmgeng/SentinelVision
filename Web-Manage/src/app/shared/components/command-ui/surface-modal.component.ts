import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, HostListener, Input, Output } from '@angular/core';
import { CommandAccent } from './command-topbar.component';

/**
 * Reusable theme-aware modal with backdrop blur, scale-fade motion, and Esc dismiss.
 */
@Component({
  selector: 'app-surface-modal',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      *ngIf="open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm sv-modal-backdrop"
      (click)="onBackdropClick()"
      role="dialog"
      aria-modal="true"
    >
      <div
        class="sv-surface-modal sv-modal-panel w-full rounded-2xl p-5 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto"
        [ngClass]="maxWidthClass"
        (click)="$event.stopPropagation()"
      >
        <div class="flex items-center justify-between border-b sv-border-subtle pb-3">
          <div class="flex items-center gap-2 font-bold" [ngClass]="titleAccentClass">
            <i *ngIf="icon" [class]="icon + ' text-lg'"></i>
            <span>{{ title }}</span>
          </div>
          <button
            type="button"
            (click)="close()"
            aria-label="Close modal"
            class="sv-text-muted hover:opacity-100 opacity-75 transition p-1 rounded-lg"
          >
            <i class="ri-close-line text-xl"></i>
          </button>
        </div>

        <div>
          <ng-content></ng-content>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 border-t sv-border-subtle">
          <ng-content select="[footer]"></ng-content>
        </div>
      </div>
    </div>
  `,
})
export class SurfaceModalComponent {
  @Input() open = false;
  @Input() title = '';
  @Input() icon = '';
  @Input() accent: CommandAccent = 'cyan';
  @Input() size: 'md' | 'lg' | 'xl' = 'lg';
  @Input() closeOnBackdrop = true;
  @Output() closed = new EventEmitter<void>();

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open) {
      this.close();
    }
  }

  onBackdropClick(): void {
    if (this.closeOnBackdrop) {
      this.close();
    }
  }

  close(): void {
    this.closed.emit();
  }

  get maxWidthClass(): string {
    if (this.size === 'md') return 'max-w-md';
    if (this.size === 'xl') return 'max-w-2xl';
    return 'max-w-lg';
  }

  get titleAccentClass(): string {
    switch (this.accent) {
      case 'purple':
        return 'text-purple-600 dark:text-purple-400';
      case 'violet':
        return 'text-violet-600 dark:text-violet-400';
      case 'emerald':
        return 'text-emerald-600 dark:text-emerald-400';
      case 'amber':
        return 'text-amber-600 dark:text-amber-400';
      case 'sky':
        return 'text-sky-600 dark:text-sky-400';
      default:
        return 'text-cyan-600 dark:text-cyan-400';
    }
  }
}
