import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../../shared/shared.module';
import { TokenService } from '../../../../shared/services/token.service';
import { HrScheduleApiService } from '../hr-schedule-api.service';
import { defaultNewShift } from '../hr-schedule.helpers';
import { HrDepartmentShiftRow, HrEmployeeShiftRow, HrShift } from '../hr-schedule.models';

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

  constructor(private api: HrScheduleApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadShifts();
    this.loadDepartmentsAndEmployees();
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
}
