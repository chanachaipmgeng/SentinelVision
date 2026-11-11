import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { EmployeeImportProgress } from '../../../services/employee.service';

@Component({
    selector: 'app-emp-import-overlay',
    imports: [CommonModule],
    template: `
    @if (isImporting) {
      <div class="fixed inset-0 z-[10050] flex items-center justify-center bg-black/40 backdrop-blur-[1px]"
        role="status" aria-live="polite" aria-busy="true">
        <div class="bg-white dark:bg-bodybg rounded-xl shadow-lg px-8 py-7 flex flex-col items-center gap-3 min-w-[260px]">
          <div class="ti-spinner animation-spin !w-10 !h-10 text-primary" role="status"></div>
          <div class="text-base font-semibold text-defaulttextcolor">กำลังนำเข้าพนักงาน...</div>
          <div class="text-sm text-textmuted text-center">{{ statusText }}</div>
          @if (progress?.total) {
            <div class="w-full h-2 rounded-full bg-light overflow-hidden" role="progressbar"
              [attr.aria-valuenow]="progress?.processed || 0" aria-valuemin="0" [attr.aria-valuemax]="progress?.total">
              <div class="h-full bg-primary transition-all"
                [style.width.%]="((progress?.processed || 0) / (progress?.total || 1)) * 100"></div>
            </div>
            <div class="text-xs text-textmuted">
              {{ progress?.processed || 0 }} / {{ progress?.total }} แถว
              · สำเร็จ {{ progress?.success || 0 }} · ไม่สำเร็จ {{ progress?.failed || 0 }}
            </div>
          }
        </div>
      </div>
    }
  `
})
export class EmpImportOverlayComponent {
  @Input() isImporting = false;
  @Input() progress: EmployeeImportProgress | null = null;
  @Input() statusText = 'กรุณารอสักครู่ ระบบกำลังบันทึกข้อมูลและใบหน้า';
}
