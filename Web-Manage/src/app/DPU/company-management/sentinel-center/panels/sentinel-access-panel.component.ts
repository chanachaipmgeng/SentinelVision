import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService } from '../sentinel-api.service';
import { buildZoneAllowedIdentityTypes, defaultZoneForm } from '../sentinel.helpers';

@Component({
  selector: 'app-sentinel-access-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './sentinel-access-panel.component.html',
})
export class SentinelAccessPanelComponent implements OnInit {
  @Output() toast = new EventEmitter<string>();
  @Output() overviewChanged = new EventEmitter<void>();

  companyId = '';
  zones: any[] = [];
  zoneForm = defaultZoneForm();

  constructor(private api: SentinelApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadZones();
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
        next: () => {
          this.zoneForm.name = '';
          this.toast.emit('สร้างโซนประตู Access Control สำเร็จ');
          this.loadZones();
          this.overviewChanged.emit();
        },
      });
  }

  remoteUnlockZone(zoneId: string): void {
    this.api
      .triggerZone(this.companyId, zoneId, 'Admin Console Remote Unlock')
      .subscribe({
        next: () => {
          this.toast.emit('ส่งคำสั่งปลดล็อกประตูเรียบร้อยแล้ว');
          this.overviewChanged.emit();
        },
      });
  }

  deleteZone(zoneId: string): void {
    this.api.deleteZone(this.companyId, zoneId).subscribe({
      next: () => {
        this.toast.emit('ลบโซนประตูเรียบร้อยแล้ว');
        this.loadZones();
        this.overviewChanged.emit();
      },
    });
  }
}
