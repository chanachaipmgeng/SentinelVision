import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { TokenService } from '../../../shared/services/token.service';
import { TimestampService } from '../../services/timestamp.service';
import swal from 'sweetalert';

type Tab = 'attendance' | 'leave' | 'regularization';

@Component({
  selector: 'app-employee-self-service',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule, PageToolbarComponent, EmptyStateComponent],
  templateUrl: './self-service.component.html',
  styleUrls: ['./self-service.component.css', '../../../shared/styles/dpu-list-page.css'],
  encapsulation: ViewEncapsulation.None,
})
export class SelfServiceComponent implements OnInit {
  companyId = '';
  memberId = '';
  companyEmployeeId = '';
  loading = false;
  activeTab: Tab = 'attendance';
  attendance: any[] = [];
  leaves: any[] = [];
  leaveBalances: any[] = [];
  leaveDraft = { startDate: '', endDate: '', leaveType: 'ANNUAL', reason: '' };
  regenDraft = {
    workDate: '',
    requestedTimestamp: '',
    requestedType: 1,
    reason: '',
  };

  constructor(
    private http: HttpClient,
    private token: TokenService,
    private timestamps: TimestampService
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
    this.memberId = this.token.getUser()?.member?.memberId || '';
  }

  ngOnInit(): void {
    if (!this.companyId || !this.memberId) return;
    this.loading = true;
    this.http.get<any>(`/employees/company/${this.companyId}/member/${this.memberId}`).subscribe({
      next: (emp) => {
        this.companyEmployeeId = emp?.company_employeeId || emp?.companyEmployeeId || '';
        this.loading = false;
        this.reload();
      },
      error: () => {
        this.loading = false;
        swal('แจ้งเตือน', 'ไม่พบบัญชีพนักงานของคุณในบริษัทนี้', 'info');
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
        .get<any>(`/hr/company/${this.companyId}/leaves`, {
          params: { company_employeeId: this.companyEmployeeId },
        })
        .subscribe({
          next: (res) => {
            this.leaves = res?.items || res || [];
            this.loading = false;
          },
          error: () => (this.loading = false),
        });
      this.http
        .get<any>(`/hr/company/${this.companyId}/leave-balances`, {
          params: { company_employeeId: this.companyEmployeeId },
        })
        .subscribe({
          next: (res) => (this.leaveBalances = res?.items || res || []),
          error: () => undefined,
        });
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
        endDate: this.leaveDraft.endDate,
        leaveType: this.leaveDraft.leaveType,
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
        },
        error: (err) => swal('Error', err?.error?.detail || 'ส่งคำขอไม่สำเร็จ', 'error'),
      });
  }
}
