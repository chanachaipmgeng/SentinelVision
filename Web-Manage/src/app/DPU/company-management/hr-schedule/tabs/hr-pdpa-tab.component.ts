import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../../shared/shared.module';
import { TokenService } from '../../../../shared/services/token.service';
import { HrScheduleApiService } from '../hr-schedule-api.service';
import {
  defaultConsentPolicy,
  defaultRetentionSettings,
  retentionFromPdpaSummary,
} from '../hr-schedule.helpers';

@Component({
  selector: 'app-hr-pdpa-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule],
  templateUrl: './hr-pdpa-tab.component.html',
})
export class HrPdpaTabComponent implements OnInit {
  @Output() status = new EventEmitter<string>();

  companyId = '';
  employees: any[] = [];
  pdpaSummary: any = null;
  consentPolicy = defaultConsentPolicy();
  retentionSettings = defaultRetentionSettings();

  constructor(private api: HrScheduleApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadEmployees();
    this.loadPdpaSummary();
  }

  private flash(msg: string): void {
    this.status.emit(msg);
  }

  loadEmployees(): void {
    this.api.getEmployees(this.companyId).subscribe((rows) => {
      this.employees = rows || [];
    });
  }

  loadPdpaSummary(): void {
    this.api.getPdpaSummary(this.companyId).subscribe((res) => {
      this.pdpaSummary = res;
      if (res?.consentPolicy) {
        this.consentPolicy = { ...this.consentPolicy, ...res.consentPolicy };
      }
      if (res?.retentionPolicy) {
        this.retentionSettings = retentionFromPdpaSummary(
          res.retentionPolicy,
          this.retentionSettings,
        );
      }
    });
    this.api.getConsentPolicy(this.companyId).subscribe((res) => {
      if (res) this.consentPolicy = { ...this.consentPolicy, ...res };
    });
    this.api.getRetention(this.companyId).subscribe((res) => {
      if (res) this.retentionSettings = { ...this.retentionSettings, ...res };
    });
  }

  saveConsentPolicy(): void {
    this.api.putConsentPolicy(this.companyId, this.consentPolicy).subscribe((res) => {
      this.consentPolicy = { ...this.consentPolicy, ...res };
      this.flash('บันทึกนโยบายความยินยอมเรียบร้อย');
    });
  }

  saveRetentionSettings(): void {
    this.api.putRetention(this.companyId, this.retentionSettings).subscribe((res) => {
      this.retentionSettings = { ...this.retentionSettings, ...res };
      this.loadPdpaSummary();
      this.flash('บันทึก Retention เรียบร้อย');
    });
  }

  exportDsar(memberId?: string): void {
    if (!memberId) return;
    this.api.exportDsar(this.companyId, memberId).subscribe((data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `dsar-${memberId}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    });
  }

  grantConsent(memberId: string): void {
    if (!memberId) return;
    this.api.grantBiometricConsent(this.companyId, memberId).subscribe(() => {
      this.loadEmployees();
      this.loadPdpaSummary();
      this.flash('บันทึกความยินยอม PDPA เรียบร้อย');
    });
  }

  revokeConsent(memberId: string): void {
    if (!memberId) return;
    this.api.revokeBiometricConsent(this.companyId, memberId).subscribe(() => {
      this.loadEmployees();
      this.loadPdpaSummary();
      this.flash('เพิกถอนความยินยอมและลบข้อมูลใบหน้าเรียบร้อย');
    });
  }
}
