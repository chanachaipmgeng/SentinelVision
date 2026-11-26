import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { ConfirmDialogService, ConfirmDialogVariant } from '../../services/confirm-dialog.service';
import { CommandAccent } from './command-topbar.component';
import { SurfaceModalComponent } from './surface-modal.component';

@Component({
  selector: 'app-confirm-dialog-host',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule, SurfaceModalComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ng-container *ngIf="dialogService.activeDialog() as active">
      <app-surface-modal
        [open]="true"
        [title]="active.options.title"
        [icon]="iconFor(active.options.variant, active.options.icon)"
        [accent]="accentFor(active.options.variant)"
        size="md"
        [closeOnBackdrop]="active.options.mode === 'alert'"
        (closed)="cancel(active.options.mode)"
      >
        <div class="space-y-3">
          <p
            *ngIf="active.options.message"
            class="text-sm sv-text-secondary whitespace-pre-line leading-relaxed mb-0"
          >
            {{ active.options.message }}
          </p>

          <div *ngIf="active.options.mode === 'prompt'" class="pt-1">
            <input
              [type]="active.options.inputType || 'text'"
              class="form-control sv-input w-full rounded-xl px-3.5 py-2 text-sm"
              [(ngModel)]="active.inputValue"
              [placeholder]="active.options.placeholder || ''"
              (keydown.enter)="submitPrompt(active.inputValue)"
              autofocus
            />
          </div>
        </div>

        <div footer class="flex items-center justify-end gap-2 w-full flex-wrap">
          <ng-container *ngIf="active.options.actions?.length; else defaultButtons">
            <button
              *ngFor="let act of active.options.actions"
              type="button"
              (click)="dialogService.close(act.value)"
              class="px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer"
              [ngClass]="actionClass(act.variant)"
            >
              {{ act.text }}
            </button>
          </ng-container>

          <ng-template #defaultButtons>
            <button
              *ngIf="active.options.mode !== 'alert'"
              type="button"
              (click)="cancel(active.options.mode)"
              class="px-4 py-2 rounded-xl text-xs font-semibold border sv-border-subtle sv-text-secondary hover:opacity-90 transition cursor-pointer"
            >
              {{ active.options.cancelText || ('common.dialog.cancel' | translate) }}
            </button>
            <button
              type="button"
              (click)="accept(active.options.mode, active.inputValue)"
              class="px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer shadow-sm"
              [ngClass]="confirmButtonClass(active.options.variant)"
            >
              {{ active.options.confirmText || (active.options.mode === 'alert' ? ('common.dialog.ok' | translate) : ('common.dialog.confirm' | translate)) }}
            </button>
          </ng-template>
        </div>
      </app-surface-modal>
    </ng-container>
  `,
})
export class ConfirmDialogHostComponent {
  readonly dialogService = inject(ConfirmDialogService);

  accept(mode: string | undefined, inputVal: string): void {
    if (mode === 'prompt') {
      this.dialogService.close(inputVal);
    } else {
      this.dialogService.close(true);
    }
  }

  submitPrompt(inputVal: string): void {
    this.dialogService.close(inputVal);
  }

  cancel(mode: string | undefined): void {
    if (mode === 'prompt') {
      this.dialogService.close(null);
    } else if (mode === 'confirm') {
      this.dialogService.close(false);
    } else {
      this.dialogService.close(undefined);
    }
  }

  accentFor(variant?: ConfirmDialogVariant): CommandAccent {
    if (variant === 'danger' || variant === 'warning') return 'amber';
    if (variant === 'success') return 'emerald';
    return 'cyan';
  }

  iconFor(variant?: ConfirmDialogVariant, custom?: string): string {
    if (custom) return custom;
    switch (variant) {
      case 'danger':
        return 'ri-error-warning-line text-rose-500';
      case 'warning':
        return 'ri-alert-line text-amber-500';
      case 'success':
        return 'ri-checkbox-circle-line text-emerald-500';
      default:
        return 'ri-information-line text-cyan-500';
    }
  }

  confirmButtonClass(variant?: ConfirmDialogVariant): string {
    switch (variant) {
      case 'danger':
        return 'bg-rose-600 hover:bg-rose-500 text-white';
      case 'warning':
        return 'bg-amber-600 hover:bg-amber-500 text-white';
      case 'success':
        return 'bg-emerald-600 hover:bg-emerald-500 text-white';
      default:
        return 'bg-teal-600 hover:bg-teal-500 text-white';
    }
  }

  actionClass(variant?: string): string {
    if (variant === 'ghost') {
      return 'border sv-border-subtle sv-text-secondary hover:opacity-90';
    }
    return this.confirmButtonClass((variant as ConfirmDialogVariant) || 'info');
  }
}
