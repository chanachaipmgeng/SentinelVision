import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { TokenService } from '../../../shared/services/token.service';
import { TimestampService } from '../../services/timestamp.service';
import { EmployeeService } from '../../services/employee.service';
import { TimestampModel } from '../../models/timestamp.model';
import swal from 'sweetalert';

@Component({
    selector: 'app-company-reports',
    imports: [CommonModule, FormsModule, SharedModule, PageToolbarComponent],
    templateUrl: './reports.component.html',
    styleUrls: ['../../../shared/styles/dpu-list-page.css'],
    encapsulation: ViewEncapsulation.None
})
export class ReportsComponent implements OnInit {
  companyId = '';
  busy = false;
  previewLoading = false;
  previewRows: TimestampModel[] = [];
  previewTotal = 0;
  employees: Array<{ company_employeeId: string; label: string }> = [];
  draft = {
    startDate: '',
    endDate: '',
    company_employeeId: '',
    mode: 'raw' as 'raw' | 'payroll',
    format: 'xlsx' as 'xlsx' | 'csv',
  };

  constructor(
    private token: TokenService,
    private timestamps: TimestampService,
    private employeesApi: EmployeeService
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  get lateCount(): number {
    return this.previewRows.filter((r) => r.isLate || (r.lateMinutes || 0) > 0).length;
  }

  get totalLateMinutes(): number {
    return this.previewRows.reduce((acc, r) => acc + Number(r.lateMinutes || 0), 0);
  }

  get totalOtMinutes(): number {
    return this.previewRows.reduce((acc, r) => acc + Number(r.overtimeMinutes || 0), 0);
  }

  get pendingOrOutCount(): number {
    return this.previewRows.filter((r) => r.timestampType === 0 || r.approvalStatus === 'PENDING').length;
  }

  ngOnInit(): void {
    const now = new Date();
    const first = new Date(now.getFullYear(), now.getMonth(), 1);
    const last = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    this.draft.startDate = this.isoDate(first);
    this.draft.endDate = this.isoDate(last);
    if (!this.companyId) return;
    this.loadPreview();
    this.employeesApi.getLists(this.companyId).subscribe({
      next: (rows: unknown[]) => {
        this.employees = (rows || []).map((row) => {
          const e = row as {
            company_employeeId?: string;
            companyEmployeeId?: string;
            employeeId?: string;
            firstName?: string;
            lastName?: string;
          };
          return {
            company_employeeId: e.company_employeeId || e.companyEmployeeId || '',
            label: `${e.employeeId || ''} — ${e.firstName || ''} ${e.lastName || ''}`.trim(),
          };
        });
      },
      error: () => undefined,
    });
  }

  loadPreview(): void {
    if (!this.companyId || this.previewLoading) return;
    this.previewLoading = true;
    this.timestamps
      .getListsSearch(
        this.companyId,
        this.draft.company_employeeId || undefined,
        this.draft.startDate || undefined,
        this.draft.endDate || undefined,
      )
      .subscribe({
        next: (rows) => {
          this.previewRows = rows || [];
          this.previewTotal = this.previewRows.length;
          this.previewLoading = false;
        },
        error: () => {
          this.previewRows = [];
          this.previewTotal = 0;
          this.previewLoading = false;
        },
      });
  }

  export(): void {
    if (!this.companyId || this.busy) return;
    this.busy = true;
    this.timestamps
      .exportReport(
        this.companyId,
        this.draft.format,
        this.draft.company_employeeId || undefined,
        this.draft.startDate || undefined,
        this.draft.endDate || undefined,
        undefined,
        undefined,
        this.draft.mode
      )
      .subscribe({
        next: (blob) => {
          this.busy = false;
          const a = document.createElement('a');
          const url = URL.createObjectURL(blob);
          a.href = url;
          a.download = `attendance-${this.draft.mode}.${this.draft.format}`;
          a.click();
          URL.revokeObjectURL(url);
        },
        error: () => {
          this.busy = false;
          swal('Error', 'ส่งออกรายงานไม่สำเร็จ', 'error');
        },
      });
  }

  private isoDate(d: Date): string {
    return d.toISOString().slice(0, 10);
  }
}
