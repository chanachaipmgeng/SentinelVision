import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { TokenService } from '../../../shared/services/token.service';
import { TimestampService } from '../../services/timestamp.service';
import { EmployeeService } from '../../services/employee.service';
import swal from 'sweetalert';

@Component({
  selector: 'app-company-reports',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule, PageToolbarComponent],
  templateUrl: './reports.component.html',
  styleUrls: ['../../../shared/styles/dpu-list-page.css'],
  encapsulation: ViewEncapsulation.None,
})
export class ReportsComponent implements OnInit {
  companyId = '';
  busy = false;
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

  ngOnInit(): void {
    const now = new Date();
    const first = new Date(now.getFullYear(), now.getMonth(), 1);
    const last = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    this.draft.startDate = this.isoDate(first);
    this.draft.endDate = this.isoDate(last);
    if (!this.companyId) return;
    this.employeesApi.getLists(this.companyId).subscribe({
      next: (rows: any[]) => {
        this.employees = (rows || []).map((e) => ({
          company_employeeId: e.company_employeeId || e.companyEmployeeId,
          label: `${e.employeeId || ''} — ${e.firstName || ''} ${e.lastName || ''}`.trim(),
        }));
      },
      error: () => undefined,
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
