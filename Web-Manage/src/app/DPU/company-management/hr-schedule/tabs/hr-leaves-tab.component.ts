import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../../shared/shared.module';
import { TokenService } from '../../../../shared/services/token.service';
import { HrScheduleApiService } from '../hr-schedule-api.service';
import { defaultNewLeave, parseLeaveList } from '../hr-schedule.helpers';

@Component({
  selector: 'app-hr-leaves-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule],
  templateUrl: './hr-leaves-tab.component.html',
})
export class HrLeavesTabComponent implements OnInit {
  @Output() status = new EventEmitter<string>();

  companyId = '';
  employees: any[] = [];
  leaves: any[] = [];
  newLeave = defaultNewLeave();

  constructor(private api: HrScheduleApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadEmployees();
    this.loadLeaves();
  }

  private flash(msg: string): void {
    this.status.emit(msg);
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
    if (!this.newLeave.company_employeeId || !this.newLeave.startDate || !this.newLeave.endDate) {
      return;
    }
    this.api.createLeave(this.companyId, this.newLeave).subscribe(() => {
      this.newLeave = defaultNewLeave();
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
