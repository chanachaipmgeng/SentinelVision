import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import swal from 'sweetalert';
import { TokenService } from '../../../../shared/services/token.service';
import { buildZoneAllowedIdentityTypes, defaultZoneForm } from '../sentinel.helpers';
import { SentinelApiService } from '../sentinel-api.service';
import { SentinelZone } from '../sentinel.models';

@Component({
    selector: 'app-sentinel-access-panel',
    imports: [CommonModule, FormsModule, RouterModule],
    templateUrl: './sentinel-access-panel.component.html'
})
export class SentinelAccessPanelComponent implements OnInit {
  /** `zones` = CRUD + Open scan; `settings` = IoT/2FA tips pointing back to zones. */
  @Input() section: 'zones' | 'settings' = 'zones';
  @Output() toast = new EventEmitter<string>();
  @Output() overviewChanged = new EventEmitter<void>();

  companyId = '';
  zones: SentinelZone[] = [];
  zoneForm = defaultZoneForm();
  lastCreatedZoneId: string | null = null;

  constructor(
    private api: SentinelApiService,
    private token: TokenService,
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadZones();
  }

  get isSettings(): boolean {
    return this.section === 'settings';
  }

  loadZones(): void {
    this.api.getZones(this.companyId).subscribe((rows) => (this.zones = rows || []));
  }

  createAccessZone(): void {
    if (!this.zoneForm.name.trim()) {
      this.toast.emit('กรุณาระบุชื่อโซนหรือประตู');
      return;
    }
    const allowedIdentityTypes = buildZoneAllowedIdentityTypes(this.zoneForm);
    this.api
      .createZone(this.companyId, { ...this.zoneForm, allowedIdentityTypes })
      .subscribe({
        next: (created) => {
          this.zoneForm.name = '';
          this.lastCreatedZoneId = created?.zoneId || null;
          this.toast.emit('สร้างโซนประตู Access Control สำเร็จ — กด “เปิดสแกน” เพื่อทดสอบ');
          this.loadZones();
          this.overviewChanged.emit();
        },
      });
  }

  remoteUnlockZone(zoneId: string): void {
    const started = performance.now();
    this.api
      .triggerZone(this.companyId, zoneId, 'Admin Console Remote Unlock')
      .subscribe({
        next: () => {
          const ms = Math.round(performance.now() - started);
          this.toast.emit(`ส่งคำสั่งปลดล็อกประตูเรียบร้อยแล้ว (${ms} ms)`);
          this.overviewChanged.emit();
        },
        error: () => {
          this.toast.emit('ไม่สามารถติดต่อ Relay / ปลดล็อกประตูไม่สำเร็จ');
        },
      });
  }

  triggerFireAlarmAll(): void {
    swal({
      title: 'ยืนยันปลดล็อกประตูฉุกเฉินทุกโซน?',
      text: 'ระบบจะสั่งเปิดประตูที่ใช้งานอยู่ทั้งหมดพร้อมกันทันที (Fire Alarm Fail-Safe)',
      icon: 'warning',
      buttons: ['ยกเลิก', 'ปลดล็อกทุกประตู'],
      dangerMode: true,
    }).then((confirmed) => {
      if (!confirmed) return;
      this.api.triggerFireAlarm(this.companyId).subscribe({
        next: (res) => {
          const count = Number(res?.['unlockedCount'] ?? this.zones.length);
          this.toast.emit(`ปลดล็อกประตูฉุกเฉินทั้งหมด ${count} โซนเรียบร้อยแล้ว`);
          this.overviewChanged.emit();
        },
        error: () => this.toast.emit('ไม่สามารถส่งคำสั่ง Fire Alarm ได้'),
      });
    });
  }

  runHealthCheck(): void {
    this.api.runHealthCheck(this.companyId).subscribe({
      next: (res) => {
        const offline = Array.isArray(res?.['offlineCameras']) ? res['offlineCameras'].length : 0;
        const held = Array.isArray(res?.['doorHeldOpen']) ? res['doorHeldOpen'].length : 0;
        this.toast.emit(`Health Check เสร็จสิ้น: กล้องออฟไลน์ ${offline} ตัว, ประตูเปิดค้าง ${held} จุด`);
        this.overviewChanged.emit();
      },
      error: () => this.toast.emit('ไม่สามารถรัน Health Check ได้'),
    });
  }

  resetFireAlarmAll(): void {
    this.api.resetFireAlarm(this.companyId).subscribe({
      next: () => {
        this.toast.emit('รีเซ็ตสถานะ Fire Alarm กลับสู่โหมดปกติแล้ว');
        this.overviewChanged.emit();
      },
      error: () => {
        this.toast.emit('ไม่สามารถรีเซ็ตสถานะ Fire Alarm ได้');
      },
    });
  }

  deleteZone(zoneId: string): void {
    this.api.deleteZone(this.companyId, zoneId).subscribe({
      next: () => {
        this.toast.emit('ลบโซนประตูเรียบร้อยแล้ว');
        if (this.lastCreatedZoneId === zoneId) this.lastCreatedZoneId = null;
        this.loadZones();
        this.overviewChanged.emit();
      },
    });
  }
}
