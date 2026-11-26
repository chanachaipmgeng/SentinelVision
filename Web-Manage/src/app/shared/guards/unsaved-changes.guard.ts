import { inject } from '@angular/core';
import { CanDeactivateFn } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { ConfirmDialogService } from '../services/confirm-dialog.service';

export interface HasUnsavedChanges {
  hasUnsavedChanges(): boolean;
}

export const unsavedChangesGuard: CanDeactivateFn<HasUnsavedChanges> = (component) => {
  if (component?.hasUnsavedChanges?.()) {
    const dialogs = inject(ConfirmDialogService);
    const translate = inject(TranslateService);
    return dialogs.confirm({
      title: translate.instant('common.dialog.unsavedTitle') || 'ยังไม่ได้บันทึกการเปลี่ยนแปลง',
      message: translate.instant('common.dialog.unsavedBody') || 'ต้องการออกจากหน้านี้โดยไม่บันทึกหรือไม่?',
      variant: 'warning',
    });
  }
  return true;
};
