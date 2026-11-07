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

@Component({
  selector: 'app-hr-holidays-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule],
  templateUrl: './hr-holidays-tab.component.html',
})
export class HrHolidaysTabComponent implements OnInit {
  @Output() status = new EventEmitter<string>();

  companyId = '';
  holidays: any[] = [];
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
      next: (res: any) => {
        this.holidayBusy = false;
        this.loadHolidays();
        const n = Number(res?.imported || 0);
        this.flash(`โหลดวันหยุดราชการไทย ${res?.year || this.holidayPresetYear} แล้ว (${n} รายการ)`);
      },
      error: (err) => {
        this.holidayBusy = false;
        this.holidayImportHint = err?.error?.detail || 'โหลด preset ไม่สำเร็จ';
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
      next: (res: any) => {
        this.holidayBusy = false;
        this.loadHolidays();
        this.flash(`นำเข้าวันหยุดแล้ว (ใหม่ ${res?.created || 0} / อัปเดต ${res?.updated || 0})`);
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
