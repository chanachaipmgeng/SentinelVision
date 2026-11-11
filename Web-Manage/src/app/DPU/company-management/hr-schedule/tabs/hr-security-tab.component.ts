import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../../shared/shared.module';
import { TokenService } from '../../../../shared/services/token.service';
import { HrScheduleApiService } from '../hr-schedule-api.service';
import { HrKioskDevice } from '../hr-schedule.models';

interface MfaStatusView {
  username?: string;
  totpEnabled?: boolean;
}

interface MfaSetupDataView {
  secret?: string;
  otpauthUri?: string;
}

@Component({
    selector: 'app-hr-security-tab',
    imports: [CommonModule, FormsModule, SharedModule],
    templateUrl: './hr-security-tab.component.html'
})
export class HrSecurityTabComponent implements OnInit {
  @Output() status = new EventEmitter<string>();

  companyId = '';
  kioskDevices: HrKioskDevice[] = [];
  newKioskName = '';
  issuedKiosk: HrKioskDevice | null = null;
  readonly pairPageUrl = `${window.location.origin}/kiosk/pair`;
  mfaStatus: MfaStatusView | null = null;
  mfaSetupData: MfaSetupDataView | null = null;
  mfaVerifyCode = '';

  constructor(private api: HrScheduleApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadKioskDevices();
    this.loadMfaStatus();
  }

  private flash(msg: string): void {
    this.status.emit(msg);
  }

  loadKioskDevices(): void {
    this.api.getKioskDevices(this.companyId).subscribe((rows) => {
      this.kioskDevices = rows || [];
    });
  }

  loadMfaStatus(): void {
    this.api.getMfaStatus().subscribe((res) => {
      this.mfaStatus = res;
    });
  }

  createKioskDevice(): void {
    if (!this.newKioskName.trim()) return;
    this.api.createKioskDevice(this.companyId, this.newKioskName).subscribe((res) => {
      this.issuedKiosk = res;
      this.newKioskName = '';
      this.loadKioskDevices();
      this.flash('สร้างอุปกรณ์และรหัสจับคู่สำเร็จ');
    });
  }

  reissueKioskPairingCode(deviceId: string): void {
    this.api.reissueKioskPairingCode(this.companyId, deviceId).subscribe((res) => {
      this.issuedKiosk = res;
      this.loadKioskDevices();
      this.flash('ออกรหัสจับคู่ใหม่แล้ว Token เดิมของอุปกรณ์ถูกยกเลิก');
    });
  }

  revokeKioskDevice(deviceId: string): void {
    this.api.revokeKioskDevice(this.companyId, deviceId).subscribe(() => {
      if (this.issuedKiosk?.deviceId === deviceId) {
        this.issuedKiosk = null;
      }
      this.loadKioskDevices();
      this.flash('เพิกถอนสิทธิ์อุปกรณ์ Kiosk แล้ว');
    });
  }

  setupMfa(): void {
    this.api.setupMfa().subscribe((res) => {
      this.mfaSetupData = res;
      this.flash('สร้างรหัส Secret สำหรับ 2FA แล้ว');
    });
  }

  enableMfa(): void {
    if (!this.mfaVerifyCode.trim()) return;
    this.api.enableMfa(this.mfaVerifyCode).subscribe(() => {
      this.mfaSetupData = null;
      this.mfaVerifyCode = '';
      this.loadMfaStatus();
      this.flash('เปิดใช้งาน 2FA สำเร็จ');
    });
  }

  disableMfa(): void {
    this.api.disableMfa().subscribe(() => {
      this.mfaSetupData = null;
      this.loadMfaStatus();
      this.flash('ปิดการใช้งาน 2FA แล้ว');
    });
  }
}
