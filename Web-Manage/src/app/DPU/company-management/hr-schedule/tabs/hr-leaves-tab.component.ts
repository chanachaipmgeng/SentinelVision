import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../../shared/shared.module';
import { TokenService } from '../../../../shared/services/token.service';
import { HrScheduleApiService } from '../hr-schedule-api.service';
import { defaultNewLeave, parseLeaveList } from '../hr-schedule.helpers';
import { HrEmployeeShiftRow, HrLeave } from '../hr-schedule.models';

@Component({
    selector: 'app-hr-leaves-tab',
    imports: [CommonModule, FormsModule, SharedModule],
    templateUrl: './hr-leaves-tab.component.html'
})
export class HrLeavesTabComponent implements OnInit {
  @Output() status = new EventEmitter<string>();

  companyId = '';
  employees: HrEmployeeShiftRow[] = [];
  leaves: HrLeave[] = [];
  newLeave: Record<string, unknown> = {
    ...defaultNewLeave(),
    leaveUnit: 'FULL_DAY',
    leaveHours: 4,
  };

  showPolicyPanel = false;
  policyBusy = false;
  leavePolicyForm = {
    leaveType: 'ANNUAL',
    annualQuotaDays: 6,
    allowCarryOver: false,
    maxCarryOverDays: 3,
    allowHalfDay: true,
    allowHourly: true,
    requireMedicalCert: false,
    medicalCertMinDays: 3,
  };
  otPolicyForm = {
    normalOtRate: 1.0,
    workdayOtRate: 1.5,
    holidayWorkRate: 2.0,
    holidayOtRate: 3.0,
    dailyWorkMinutes: 480,
    roundingMinutes: 15,
  };

  constructor(
    private api: HrScheduleApiService,
    private http: HttpClient,
    private token: TokenService
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadEmployees();
    this.loadLeaves();
    this.loadPolicies();
  }

  private flash(msg: string): void {
    this.status.emit(msg);
  }

  loadPolicies(): void {
    this.http.get<{ items: Record<string, unknown>[] }>(`/hr/company/${this.companyId}/leave-policies`).subscribe({
      next: (res) => {
        const hit = (res.items || []).find((p) => p['leaveType'] === this.leavePolicyForm.leaveType);
        if (hit) {
          this.leavePolicyForm = {
            leaveType: String(hit['leaveType'] || 'ANNUAL'),
            annualQuotaDays: Number(hit['annualQuotaDays'] ?? 6),
            allowCarryOver: Boolean(hit['allowCarryOver']),
            maxCarryOverDays: Number(hit['maxCarryOverDays'] ?? 0),
            allowHalfDay: Boolean(hit['allowHalfDay'] ?? true),
            allowHourly: Boolean(hit['allowHourly'] ?? true),
            requireMedicalCert: Boolean(hit['requireMedicalCert']),
            medicalCertMinDays: Number(hit['medicalCertMinDays'] ?? 3),
          };
        }
      },
      error: () => undefined,
    });
    this.http.get<Record<string, unknown>>(`/hr/company/${this.companyId}/ot-policy`).subscribe({
      next: (res) => {
        this.otPolicyForm = {
          normalOtRate: Number(res['normalOtRate'] ?? 1.0),
          workdayOtRate: Number(res['workdayOtRate'] ?? 1.5),
          holidayWorkRate: Number(res['holidayWorkRate'] ?? 2.0),
          holidayOtRate: Number(res['holidayOtRate'] ?? 3.0),
          dailyWorkMinutes: Number(res['dailyWorkMinutes'] ?? 480),
          roundingMinutes: Number(res['roundingMinutes'] ?? 15),
        };
      },
      error: () => undefined,
    });
  }

  saveLeavePolicy(): void {
    if (!this.companyId || this.policyBusy) return;
    this.policyBusy = true;
    this.http
      .put(`/hr/company/${this.companyId}/leave-policies/${this.leavePolicyForm.leaveType}`, this.leavePolicyForm)
      .subscribe({
        next: () => {
          this.policyBusy = false;
          this.flash('บันทึกนโยบายวันลาแล้ว');
        },
        error: () => {
          this.policyBusy = false;
        },
      });
  }

  saveOtPolicy(): void {
    if (!this.companyId || this.policyBusy) return;
    this.policyBusy = true;
    this.http.put(`/hr/company/${this.companyId}/ot-policy`, this.otPolicyForm).subscribe({
      next: () => {
        this.policyBusy = false;
        this.flash('บันทึกอัตรา OT แล้ว');
      },
      error: () => {
        this.policyBusy = false;
      },
    });
  }

  loadEmployees(): void {
    this.api.getEmployees(this.companyId).subscribe((rows) => {
      this.employees = rows || [];
    });
  }

  loadLeaves(): void {
    this.api.getLeaves(this.companyId).subscribe((res) => {
      this.leaves = parseLeaveList(res);
    });
  }

  createLeave(): void {
    if (!this.newLeave['company_employeeId'] || !this.newLeave['startDate'] || !this.newLeave['endDate']) {
      return;
    }
    this.api.createLeave(this.companyId, this.newLeave).subscribe(() => {
      this.newLeave = { ...defaultNewLeave(), leaveUnit: 'FULL_DAY', leaveHours: 4 };
      this.loadLeaves();
      this.flash('บันทึกใบลาเรียบร้อย');
    });
  }

  decideLeave(leaveId: string, status: number): void {
    this.api.approveLeave(this.companyId, leaveId, status).subscribe(() => {
      this.loadLeaves();
      this.flash(status === 1 ? 'อนุมัติใบลาแล้ว' : 'ปฏิเสธใบลาแล้ว');
    });
  }
}
