import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../../shared/shared.module';
import { TokenService } from '../../../../shared/services/token.service';
import { HrScheduleApiService } from '../hr-schedule-api.service';
import { defaultNotifySettings } from '../hr-schedule.helpers';

@Component({
  selector: 'app-hr-observability-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule],
  templateUrl: './hr-observability-tab.component.html',
})
export class HrObservabilityTabComponent implements OnInit {
  @Output() status = new EventEmitter<string>();

  companyId = '';
  obsSummary: any = null;
  outboxLogs: any[] = [];
  notifySettings = defaultNotifySettings();

  constructor(private api: HrScheduleApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadObservabilityAndWebhooks();
  }

  private flash(msg: string): void {
    this.status.emit(msg);
  }

  loadObservabilityAndWebhooks(): void {
    this.api.getObservabilitySummary().subscribe((res) => {
      this.obsSummary = res;
    });
    this.api.getNotifySettings(this.companyId).subscribe((res) => {
      if (res) {
        this.notifySettings = { ...this.notifySettings, ...res };
      }
    });
    this.api.getOutbox(this.companyId).subscribe((rows) => {
      this.outboxLogs = rows || [];
    });
  }

  saveNotifySettings(): void {
    this.api.putNotifySettings(this.companyId, this.notifySettings).subscribe((res) => {
      if (res) {
        this.notifySettings = { ...this.notifySettings, ...res };
      }
      this.flash('บันทึกการตั้งค่า Signed Webhook เรียบร้อย');
    });
  }

  sendTestWebhook(): void {
    this.api.sendTestWebhook(this.companyId).subscribe(() => {
      this.loadObservabilityAndWebhooks();
      this.flash('ส่ง Test Webhook เข้าคิว Outbox แล้ว');
    });
  }
}
