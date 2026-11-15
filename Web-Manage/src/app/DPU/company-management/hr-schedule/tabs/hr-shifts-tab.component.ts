import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../../shared/shared.module';
import { TokenService } from '../../../../shared/services/token.service';
import { HrScheduleApiService } from '../hr-schedule-api.service';
import { defaultNewShift } from '../hr-schedule.helpers';
import { HrDepartmentShiftRow, HrEmployeeShiftRow, HrShift } from '../hr-schedule.models';

export interface RosterEntryRow {
  rosterId?: string;
  company_employeeId: string;
  workDate: string;
  shiftId: string | null;
  shiftName?: string | null;
  isDayOff?: boolean;
  isFlexible?: boolean;
}

export interface ShiftSwapRow {
  swapId: string;
  requesterEmployeeId: string;
  targetEmployeeId: string;
  workDate: string;
  requesterShiftId?: string | null;
  targetShiftId?: string | null;
  reason?: string | null;
  status: string;
  createdAt?: string | null;
}

@Component({
    selector: 'app-hr-shifts-tab',
    imports: [CommonModule, FormsModule, SharedModule],
    templateUrl: './hr-shifts-tab.component.html'
})
export class HrShiftsTabComponent implements OnInit {
  @Output() status = new EventEmitter<string>();

  companyId = '';
  shifts: HrShift[] = [];
  departments: HrDepartmentShiftRow[] = [];
  employees: HrEmployeeShiftRow[] = [];
  newShift = defaultNewShift();

  // BL-10: Roster Calendar & Shift Swap
  rosterMonth = new Date().toISOString().slice(0, 7);
  rosterDays: string[] = [];
  rosterMap: Record<string, RosterEntryRow> = {};
  shiftSwaps: ShiftSwapRow[] = [];
  genWorkDays = 5;
  genOffDays = 2;
  genFlexible = false;
  genShiftId = '';

  constructor(
    private api: HrScheduleApiService,
    private token: TokenService,
    private http: HttpClient
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadShifts();
    this.loadDepartmentsAndEmployees();
    this.loadRoster();
    this.loadShiftSwaps();
  }

  private flash(msg: string): void {
    this.status.emit(msg);
  }

  loadShifts(): void {
    this.api.getShifts(this.companyId).subscribe((res) => {
      this.shifts = res?.shifts || [];
    });
  }

  loadDepartmentsAndEmployees(): void {
    this.api.getDepartments(this.companyId).subscribe((rows) => {
      this.departments = rows || [];
    });
    this.api.getEmployees(this.companyId).subscribe((rows) => {
      this.employees = rows || [];
    });
  }

  createShift(): void {
    if (!this.newShift.name.trim()) return;
    this.api.createShift(this.companyId, this.newShift).subscribe(() => {
      this.newShift = defaultNewShift();
      this.loadShifts();
      this.flash('บันทึกกะเวลาทำงานเรียบร้อย');
    });
  }

  deleteShift(shiftId: string): void {
    this.api.deleteShift(this.companyId, shiftId).subscribe(() => {
      this.loadShifts();
      this.loadDepartmentsAndEmployees();
      this.flash('ลบกะเวลาทำงานเรียบร้อย');
    });
  }

  assignDeptShift(departmentId: string, shiftId: string): void {
    this.api
      .assignShift(this.companyId, { departmentId, shiftId: shiftId || null })
      .subscribe(() => this.flash('อัปเดตกะเวลาทำงานของแผนกแล้ว'));
  }

  assignEmpShift(company_employeeId: string, shiftId: string): void {
    this.api
      .assignShift(this.companyId, { company_employeeId, shiftId: shiftId || null })
      .subscribe(() => this.flash('อัปเดตกะเวลาทำงานรายบุคคลแล้ว'));
  }

  private buildMonthDays(ym: string): string[] {
    const [yStr, mStr] = ym.split('-');
    const y = Number(yStr) || new Date().getFullYear();
    const m = Number(mStr) || new Date().getMonth() + 1;
    const total = new Date(y, m, 0).getDate();
    const out: string[] = [];
    for (let d = 1; d <= total; d++) {
      out.push(`${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`);
    }
    return out;
  }

  loadRoster(): void {
    this.rosterDays = this.buildMonthDays(this.rosterMonth);
    if (!this.rosterDays.length) return;
    const startDate = this.rosterDays[0];
    const endDate = this.rosterDays[this.rosterDays.length - 1];
    this.http
      .get<RosterEntryRow[]>(`/hr/company/${this.companyId}/roster`, {
        params: { startDate, endDate },
      })
      .subscribe((rows) => {
        const next: Record<string, RosterEntryRow> = {};
        for (const r of rows || []) {
          next[`${r.company_employeeId}|${r.workDate}`] = r;
        }
        this.rosterMap = next;
      });
  }

  getRosterValue(empId: string, day: string): string {
    const entry = this.rosterMap[`${empId}|${day}`];
    if (!entry) return '';
    if (entry.isDayOff) return '__OFF__';
    return entry.shiftId || '';
  }

  updateRosterCell(empId: string, day: string, val: string): void {
    const isDayOff = val === '__OFF__';
    const shiftId = !val || isDayOff ? null : val;
    this.http
      .put(`/hr/company/${this.companyId}/roster`, {
        entries: [
          {
            company_employeeId: empId,
            workDate: day,
            shiftId,
            isDayOff,
          },
        ],
      })
      .subscribe(() => {
        this.rosterMap[`${empId}|${day}`] = {
          company_employeeId: empId,
          workDate: day,
          shiftId,
          isDayOff,
        };
        this.flash(`บันทึกตารางเวรวันที่ ${day} แล้ว`);
      });
  }

  generateRotatingRoster(): void {
    if (!this.rosterDays.length || !this.employees.length) return;
    const patternShiftIds = this.genShiftId
      ? [this.genShiftId]
      : this.shifts.map((s) => s.shiftId);
    this.http
      .put(`/hr/company/${this.companyId}/roster`, {
        generate: {
          employeeIds: this.employees.map((e) => e.company_employeeId),
          startDate: this.rosterDays[0],
          endDate: this.rosterDays[this.rosterDays.length - 1],
          patternShiftIds,
          workDays: Number(this.genWorkDays) || 5,
          offDays: Number(this.genOffDays) || 2,
          isFlexible: this.genFlexible,
        },
      })
      .subscribe(() => {
        this.loadRoster();
        this.flash('สร้างตารางเวรหมุนเวียนทั้งเดือนเรียบร้อย');
      });
  }

  loadShiftSwaps(): void {
    this.http
      .get<ShiftSwapRow[]>(`/hr/company/${this.companyId}/shift-swaps`)
      .subscribe((rows) => {
        this.shiftSwaps = rows || [];
      });
  }

  decideShiftSwap(swapId: string, decision: 'APPROVED' | 'REJECTED'): void {
    this.http
      .post(`/hr/company/${this.companyId}/shift-swaps/${swapId}/approval`, {
        status: decision,
      })
      .subscribe(() => {
        this.loadShiftSwaps();
        this.loadRoster();
        this.flash(decision === 'APPROVED' ? 'อนุมัติการสลับกะแล้ว' : 'ปฏิเสธคำขอสลับกะแล้ว');
      });
  }

  employeeNameById(empId: string): string {
    const emp = this.employees.find((e) => e.company_employeeId === empId);
    if (!emp) return empId.slice(0, 8);
    return `${emp.member?.firstName || ''} ${emp.member?.lastName || ''}`.trim() || emp.employeeId || empId.slice(0, 8);
  }
}
