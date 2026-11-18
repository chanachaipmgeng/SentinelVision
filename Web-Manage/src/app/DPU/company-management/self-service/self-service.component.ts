import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { TokenService } from '../../../shared/services/token.service';
import { PermissionService } from '../../../shared/services/permission.service';
import { TimestampService } from '../../services/timestamp.service';
import swal from 'sweetalert';

type Tab = 'attendance' | 'leave' | 'regularization' | 'ot' | 'swap';

interface SelfAttendanceRow {
  timestamp?: string;
  createdAt?: string;
  timestampTypeText?: string;
  timestampType?: string | number;
  approvalStatusText?: string;
  approvalStatus?: string;
  note?: string;
}

interface SelfLeaveRow {
  leaveId?: string;
  status?: string | number;
  approvalStatus?: string;
  leaveType?: string;
  startDate?: string;
  endDate?: string;
  reason?: string;
}

interface SelfLeaveBalanceRow {
  leaveType?: string;
  balance?: number;
  used?: number;
  remainingDays?: number;
}

interface SelfRegularizationRow {
  id?: string;
  workDate?: string;
  requestedTimestamp?: string;
  requestedType?: number | string;
  status?: string;
  reason?: string;
  createdAt?: string;
}

interface SelfOtRow {
  id?: string;
  workDate?: string;
  otMinutes?: number;
  status?: string;
  reason?: string;
  createdAt?: string;
}

@Component({
    selector: 'app-employee-self-service',
    imports: [CommonModule, FormsModule, RouterModule, SharedModule, PageToolbarComponent, EmptyStateComponent],
    templateUrl: './self-service.component.html',
    styleUrls: ['./self-service.component.css', '../../../shared/styles/dpu-list-page.css'],
    encapsulation: ViewEncapsulation.None
})
export class SelfServiceComponent implements OnInit {
  companyId = '';
  memberId = '';
  companyEmployeeId = '';
  loading = false;
  /** True when signed-in identity is company/HR admin (employee portal audience). */
  isCompanyAdminViewer = false;
  /** Allows Admin/HR with a linked CompanyEmployee record to toggle into their own Self-Service view. */
  adminSelfServiceMode = true;
  /** No CompanyEmployee row for this member in the selected company. */
  missingEmployeeRecord = false;
  loadError = '';
  activeTab: Tab = 'attendance';
  attendance: SelfAttendanceRow[] = [];
  leaves: SelfLeaveRow[] = [];
  leaveBalances: SelfLeaveBalanceRow[] = [];
  regularizations: SelfRegularizationRow[] = [];
  otRequests: SelfOtRow[] = [];
  leaveDraft = {
    startDate: '',
    endDate: '',
    leaveType: 'ANNUAL',
    leaveUnit: 'DAY' as 'DAY' | 'HOUR',
    leaveHours: 4,
    attachmentUrl: '',
    reason: '',
  };
  regenDraft = {
    workDate: '',
    requestedTimestamp: '',
    requestedType: 1,
    reason: '',
  };
  otDraft = {
    workDate: '',
    otMinutes: 60,
    reason: '',
  };
  shiftSwaps: Array<{ swapId: string; workDate: string; requesterEmployeeId: string; targetEmployeeId: string; status: string; reason?: string }> = [];
  colleagues: Array<{ company_employeeId: string; employeeId?: string; member?: { firstName?: string; lastName?: string } }> = [];
  swapDraft = { targetEmployeeId: '', workDate: '', reason: '' };

  constructor(
    private http: HttpClient,
    private token: TokenService,
    private timestamps: TimestampService,
    private permissions: PermissionService
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
    this.memberId = this.token.getUser()?.member?.memberId || '';
  }

  /** Show the employee-oriented empty panel instead of admin-looking blank tables. */
  get showEmployeeAudienceEmpty(): boolean {
    if (this.loading) return false;
    if (this.missingEmployeeRecord) return true;
    return this.isCompanyAdminViewer && !this.adminSelfServiceMode;
  }

  toggleAdminSelfServiceMode(): void {
    this.adminSelfServiceMode = !this.adminSelfServiceMode;
    if (this.adminSelfServiceMode && this.companyEmployeeId && this.attendance.length === 0 && this.leaves.length === 0) {
      this.reload();
    }
  }

  ngOnInit(): void {
    this.isCompanyAdminViewer = this.permissions.isCompanyAdmin();
    if (!this.companyId || !this.memberId) {
      this.missingEmployeeRecord = true;
      return;
    }
    this.loading = true;
    this.loadError = '';
    this.permissions.load(this.companyId).subscribe({
      next: () => {
        this.isCompanyAdminViewer = this.permissions.isCompanyAdmin();
        // Company admin: stop after role check — page is employee-audience only.
        if (this.isCompanyAdminViewer) {
          this.loading = false;
        }
      },
      error: () => {
        if (this.isCompanyAdminViewer) {
          this.loading = false;
        }
      },
    });
    // Employees (and non-admin deep links) resolve their CompanyEmployee row.
    this.http
      .get<{ company_employeeId?: string; companyEmployeeId?: string }>(
        `/employees/company/${this.companyId}/member/${this.memberId}`,
      )
      .subscribe({
      next: (emp) => {
        this.companyEmployeeId = emp?.company_employeeId || emp?.companyEmployeeId || '';
        this.missingEmployeeRecord = !this.companyEmployeeId;
        this.loading = false;
        if (this.companyEmployeeId && (!this.isCompanyAdminViewer || this.adminSelfServiceMode)) {
          this.reload();
        }
      },
      error: () => {
        this.missingEmployeeRecord = true;
        this.companyEmployeeId = '';
        this.loading = false;
        if (!this.isCompanyAdminViewer) {
          this.loadError = 'ไม่พบบัญชีพนักงานของคุณในบริษัทนี้';
        }
      },
    });
  }

  setTab(tab: Tab): void {
    this.activeTab = tab;
    this.reload();
  }

  reload(): void {
    if (!this.companyId || !this.companyEmployeeId) return;
    this.loading = true;
    if (this.activeTab === 'attendance') {
      this.timestamps
        .getListsSearch(this.companyId, this.companyEmployeeId)
        .subscribe({
          next: (rows) => {
            this.attendance = rows || [];
            this.loading = false;
          },
          error: () => (this.loading = false),
        });
    } else if (this.activeTab === 'leave') {
      this.http
        .get<SelfLeaveRow[] | { items?: SelfLeaveRow[] }>(`/hr/company/${this.companyId}/leaves`, {
          params: { company_employeeId: this.companyEmployeeId },
        })
        .subscribe({
          next: (res) => {
            this.leaves = Array.isArray(res) ? res : res?.items || [];
            this.loading = false;
          },
          error: () => (this.loading = false),
        });
      this.http
        .get<SelfLeaveBalanceRow[] | { items?: SelfLeaveBalanceRow[] }>(
          `/hr/company/${this.companyId}/leave-balances`,
          {
          params: { company_employeeId: this.companyEmployeeId },
        })
        .subscribe({
          next: (res) =>
            (this.leaveBalances = Array.isArray(res) ? res : res?.items || []),
          error: () => undefined,
        });
    } else if (this.activeTab === 'regularization') {
      this.http
        .get<SelfRegularizationRow[] | { items?: SelfRegularizationRow[] }>(
          `/hr/company/${this.companyId}/regularizations`,
          { params: { company_employeeId: this.companyEmployeeId } }
        )
        .subscribe({
          next: (res) => {
            this.regularizations = Array.isArray(res) ? res : res?.items || [];
            this.loading = false;
          },
          error: () => (this.loading = false),
        });
    } else if (this.activeTab === 'ot') {
      this.http
        .get<SelfOtRow[] | { items?: SelfOtRow[] }>(
          `/hr/company/${this.companyId}/ot-approvals`,
          { params: { company_employeeId: this.companyEmployeeId } }
        )
        .subscribe({
          next: (res) => {
            this.otRequests = Array.isArray(res) ? res : res?.items || [];
            this.loading = false;
          },
          error: () => (this.loading = false),
        });
    } else if (this.activeTab === 'swap') {
      this.http
        .get<typeof this.shiftSwaps>(`/hr/company/${this.companyId}/shift-swaps`, {
          params: { company_employeeId: this.companyEmployeeId },
        })
        .subscribe({
          next: (rows) => {
            this.shiftSwaps = rows || [];
            this.loading = false;
          },
          error: () => (this.loading = false),
        });
      if (!this.colleagues.length) {
        this.http
          .get<typeof this.colleagues>(`/employees/company/${this.companyId}`)
          .subscribe({
            next: (rows) =>
              (this.colleagues = (rows || []).filter(
                (e) => e.company_employeeId !== this.companyEmployeeId
              )),
            error: () => undefined,
          });
      }
    } else {
      this.loading = false;
    }
  }

  submitLeave(): void {
    if (!this.companyEmployeeId) return;
    this.http
      .post(`/hr/company/${this.companyId}/leaves`, {
        company_employeeId: this.companyEmployeeId,
        startDate: this.leaveDraft.startDate,
        endDate: this.leaveDraft.endDate || this.leaveDraft.startDate,
        leaveType: this.leaveDraft.leaveType,
        leaveUnit: this.leaveDraft.leaveUnit,
        leaveHours: this.leaveDraft.leaveUnit === 'HOUR' ? Number(this.leaveDraft.leaveHours) || 1 : null,
        attachmentUrl: this.leaveDraft.attachmentUrl?.trim() || null,
        reason: this.leaveDraft.reason,
      })
      .subscribe({
        next: () => {
          swal('สำเร็จ', 'ส่งคำขอลาแล้ว', 'success');
          this.reload();
        },
        error: (err) => swal('Error', err?.error?.detail || 'ส่งคำขอไม่สำเร็จ', 'error'),
      });
  }

  submitRegularization(): void {
    if (!this.companyEmployeeId) return;
    const ts = this.regenDraft.requestedTimestamp
      ? new Date(this.regenDraft.requestedTimestamp).toISOString()
      : '';
    this.http
      .post(`/hr/company/${this.companyId}/regularizations`, {
        company_employeeId: this.companyEmployeeId,
        workDate: this.regenDraft.workDate,
        requestedTimestamp: ts,
        requestedType: this.regenDraft.requestedType,
        reason: this.regenDraft.reason,
      })
      .subscribe({
        next: () => {
          swal('สำเร็จ', 'ส่งคำขอแก้เวลาแล้ว', 'success');
          this.regenDraft = { workDate: '', requestedTimestamp: '', requestedType: 1, reason: '' };
          this.reload();
        },
        error: (err) => swal('Error', err?.error?.detail || 'ส่งคำขอไม่สำเร็จ', 'error'),
      });
  }

  submitOt(): void {
    if (!this.companyEmployeeId) return;
    this.http
      .post(`/hr/company/${this.companyId}/ot-approvals`, {
        company_employeeId: this.companyEmployeeId,
        workDate: this.otDraft.workDate,
        otMinutes: Number(this.otDraft.otMinutes) || 60,
        reason: this.otDraft.reason,
      })
      .subscribe({
        next: () => {
          swal('สำเร็จ', 'ส่งคำขอ OT แล้ว', 'success');
          this.otDraft = { workDate: '', otMinutes: 60, reason: '' };
          this.reload();
        },
        error: (err) => swal('Error', err?.error?.detail || 'ส่งคำขอไม่สำเร็จ', 'error'),
      });
  }

  submitShiftSwap(): void {
    if (!this.companyEmployeeId || !this.swapDraft.targetEmployeeId || !this.swapDraft.workDate) return;
    this.http
      .post(`/hr/company/${this.companyId}/shift-swaps`, {
        requesterEmployeeId: this.companyEmployeeId,
        targetEmployeeId: this.swapDraft.targetEmployeeId,
        workDate: this.swapDraft.workDate,
        reason: this.swapDraft.reason,
      })
      .subscribe({
        next: () => {
          swal('สำเร็จ', 'ส่งคำขอสลับกะแล้ว รอหัวหน้าอนุมัติ', 'success');
          this.swapDraft = { targetEmployeeId: '', workDate: '', reason: '' };
          this.reload();
        },
        error: (err) => swal('Error', err?.error?.detail || 'ส่งคำขอสลับกะไม่สำเร็จ', 'error'),
      });
  }
}
