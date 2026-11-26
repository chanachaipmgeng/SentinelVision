import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { CommandAccent } from './command-topbar.component';

let nextModalId = 0;

/**
 * Reusable theme-aware modal with backdrop blur, scale-fade motion, focus trap, and Esc dismiss.
 */
@Component({
  selector: 'app-surface-modal',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      *ngIf="open"
      [attr.id]="modalId || null"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm sv-modal-backdrop"
      (click)="onBackdropClick()"
      role="dialog"
      aria-modal="true"
      [attr.aria-labelledby]="titleId"
    >
      <div
        #modalPanel
        class="sv-surface-modal sv-modal-panel w-full rounded-2xl p-5 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto"
        [ngClass]="maxWidthClass"
        (click)="$event.stopPropagation()"
      >
        <div class="flex items-start justify-between gap-3 border-b sv-border-subtle pb-3">
          <div>
            <div [id]="titleId" class="flex items-center gap-2 font-bold" [ngClass]="titleAccentClass">
              <i *ngIf="icon" [class]="icon + ' text-lg'" aria-hidden="true"></i>
              <span>{{ title }}</span>
            </div>
            <p *ngIf="subtitle" class="mb-0 mt-0.5 text-xs sv-text-muted">{{ subtitle }}</p>
          </div>
          <button
            type="button"
            (click)="close()"
            aria-label="Close modal"
            class="sv-text-muted hover:opacity-100 opacity-75 transition p-1 rounded-lg"
          >
            <i class="ri-close-line text-xl" aria-hidden="true"></i>
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
export class SurfaceModalComponent implements OnChanges, OnDestroy {
  @Input() open = false;
  @Input() modalId?: string;
  @Input() title = '';
  @Input() subtitle = '';
  @Input() icon = '';
  @Input() accent: CommandAccent = 'cyan';
  @Input() size: 'md' | 'lg' | 'xl' | '2xl' = 'lg';
  @Input() closeOnBackdrop = true;
  @Output() closed = new EventEmitter<void>();

  @ViewChild('modalPanel') modalPanel?: ElementRef<HTMLElement>;

  readonly titleId = `sv-modal-title-${++nextModalId}`;
  private previousActive: HTMLElement | null = null;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['open']) {
      if (this.open) {
        this.previousActive =
          typeof document !== 'undefined' ? (document.activeElement as HTMLElement | null) : null;
        setTimeout(() => this.focusFirstElement(), 0);
      } else {
        this.restoreFocus();
      }
    }
  }

  ngOnDestroy(): void {
    if (this.open) {
      this.restoreFocus();
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open) {
      this.close();
    }
  }

  @HostListener('document:keydown', ['$event'])
  onKeydown(event: KeyboardEvent): void {
    if (!this.open || event.key !== 'Tab') return;
    const panel = this.modalPanel?.nativeElement;
    if (!panel) return;
    const focusables = this.getFocusableElements(panel);
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement as HTMLElement | null;
    if (event.shiftKey) {
      if (active === first || !panel.contains(active)) {
        event.preventDefault();
        last.focus();
      }
    } else if (active === last || !panel.contains(active)) {
      event.preventDefault();
      first.focus();
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

  private focusFirstElement(): void {
    const panel = this.modalPanel?.nativeElement;
    if (!panel) return;
    const focusables = this.getFocusableElements(panel);
    const preferred =
      focusables.find((el) => el.hasAttribute('autofocus') || el.tagName === 'INPUT') || focusables[0];
    preferred?.focus();
  }

  private restoreFocus(): void {
    if (this.previousActive && typeof this.previousActive.focus === 'function') {
      try {
        this.previousActive.focus();
      } catch {
        /* ignore detached element */
      }
    }
    this.previousActive = null;
  }

  private getFocusableElements(root: HTMLElement): HTMLElement[] {
    const selector =
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    return Array.from(root.querySelectorAll<HTMLElement>(selector)).filter(
      (el) => el.offsetParent !== null || el === document.activeElement,
    );
  }

  get maxWidthClass(): string {
    if (this.size === 'md') return 'max-w-md';
    if (this.size === 'xl') return 'max-w-2xl';
    if (this.size === '2xl') return 'max-w-4xl';
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
