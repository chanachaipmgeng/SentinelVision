import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../../shared/shared.module';
import { TokenService } from '../../../../shared/services/token.service';
import { HrScheduleApiService } from '../hr-schedule-api.service';
import {
  defaultNewHoliday,
  holidayImportFormat,
  holidaySourceLabel,
} from '../hr-schedule.helpers';
import { HrHoliday } from '../hr-schedule.models';
import { HttpErrorResponse } from '@angular/common/http';
import { apiErrorMessage } from '../../../../shared/utils/http-error-body';

@Component({
    selector: 'app-hr-holidays-tab',
    imports: [CommonModule, FormsModule, SharedModule],
    templateUrl: './hr-holidays-tab.component.html'
})
export class HrHolidaysTabComponent implements OnInit {
  @Output() status = new EventEmitter<string>();

  companyId = '';
  holidays: HrHoliday[] = [];
  holidayBusy = false;
  holidayImportHint = '';
  holidayPresetYear = new Date().getFullYear();
  newHoliday = defaultNewHoliday();

  constructor(private api: HrScheduleApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadHolidays();
  }

  private flash(msg: string): void {
    this.status.emit(msg);
  }

  holidaySourceLabel = holidaySourceLabel;

  loadHolidays(): void {
    this.api.getHolidays(this.companyId).subscribe((rows) => {
      this.holidays = rows || [];
    });
  }

  createHoliday(): void {
    if (!this.newHoliday.holidayDate || !this.newHoliday.name.trim()) return;
    this.api.createHoliday(this.companyId, this.newHoliday).subscribe(() => {
      this.newHoliday = defaultNewHoliday();
      this.loadHolidays();
      this.flash('เพิ่มวันหยุดบริษัทเรียบร้อย');
    });
  }

  deleteHoliday(holidayId: string): void {
    this.api.deleteHoliday(this.companyId, holidayId).subscribe(() => {
      this.loadHolidays();
      this.flash('ลบวันหยุดบริษัทเรียบร้อย');
    });
  }

  applyThaiHolidayPreset(): void {
    if (!this.companyId || this.holidayBusy) return;
    this.holidayBusy = true;
    this.holidayImportHint = '';
    this.api.applyThaiHolidayPreset(this.companyId, this.holidayPresetYear).subscribe({
      next: (res) => {
        this.holidayBusy = false;
        this.loadHolidays();
        const record = res as { imported?: number; year?: number };
        const n = Number(record.imported || 0);
        this.flash(`โหลดวันหยุดราชการไทย ${record.year || this.holidayPresetYear} แล้ว (${n} รายการ)`);
      },
      error: (err: HttpErrorResponse) => {
        this.holidayBusy = false;
        this.holidayImportHint = apiErrorMessage(err, 'โหลด preset ไม่สำเร็จ');
      },
    });
  }

  onHolidayFileSelected(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    const file = input?.files?.[0];
    if (!file || !this.companyId) return;
    this.holidayBusy = true;
    this.holidayImportHint = '';
    const form = new FormData();
    form.append('file', file, file.name);
    form.append('format', holidayImportFormat(file.name));
    this.api.importHolidays(this.companyId, form).subscribe({
      next: (res) => {
        this.holidayBusy = false;
        this.loadHolidays();
        const record = res as { created?: number; updated?: number };
        this.flash(`นำเข้าวันหยุดแล้ว (ใหม่ ${record.created || 0} / อัปเดต ${record.updated || 0})`);
        if (input) input.value = '';
      },
      error: (err) => {
        this.holidayBusy = false;
        this.holidayImportHint = err?.error?.detail || 'นำเข้าไฟล์ไม่สำเร็จ';
        if (input) input.value = '';
      },
    });
  }
}
