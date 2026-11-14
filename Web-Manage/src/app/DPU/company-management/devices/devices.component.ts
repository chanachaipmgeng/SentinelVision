import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { PillSearchComponent } from '../../../shared/components/pill-search/pill-search.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { SimplePagerComponent } from '../../../shared/components/simple-pager/simple-pager.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { SideDrawerComponent } from '../../../shared/components/side-drawer/side-drawer.component';
import { TokenService } from '../../../shared/services/token.service';
import { VALID_STATION_MODES } from '../../services/company-module-config.service';
import { KeyboardTableDirective } from '../../../shared/directives/keyboard-table.directive';
import { LocaleDatePipe } from '../../../shared/pipes/locale-date.pipe';
import swal from 'sweetalert';

export interface KioskDeviceRow {
  deviceId: string;
  companyId: string;
  name: string;
  locationId?: string | null;
  locationLabel?: string | null;
  fingerprint?: string | null;
  appVersion?: string | null;
  heartbeatAt?: string | null;
  lastSeenAt?: string | null;
  stationMode?: string | null;
  zoneId?: string | null;
  config?: Record<string, unknown>;
  isPaired?: boolean;
  pairingPending?: boolean;
  pairingExpiresAt?: string | null;
  pairingCode?: string;
  revokedAt?: string | null;
  isActive?: boolean;
  createdAt?: string | null;
}

@Component({
    selector: 'app-company-devices',
    imports: [
        CommonModule,
        FormsModule,
        RouterLink,
        SharedModule,
        PageToolbarComponent,
        PillSearchComponent,
        StatChipComponent,
        SimplePagerComponent,
        EmptyStateComponent,
        SideDrawerComponent,
        KeyboardTableDirective,
        LocaleDatePipe,
    ],
    templateUrl: './devices.component.html',
    styleUrls: ['../../../shared/styles/dpu-list-page.css'],
    encapsulation: ViewEncapsulation.None
})
export class DevicesComponent implements OnInit {
  readonly pageSize = 10;
  readonly stationModes = VALID_STATION_MODES;

  companyId = '';
  loading = false;
  items: KioskDeviceRow[] = [];
  filtered: KioskDeviceRow[] = [];
  pageItems: KioskDeviceRow[] = [];
  pageIndex = 0;
  private _searchTerm = '';

  createOpen = false;
  detailOpen = false;
  selected: KioskDeviceRow | null = null;

  draft = {
    name: '',
    locationLabel: '',
    stationMode: 'ATTENDANCE' as string,
    zoneId: '',
    appVersion: '',
  };
  lastPairingCode = '';

  get searchTerm(): string {
    return this._searchTerm;
  }
  set searchTerm(val: string) {
    this._searchTerm = val;
    this.pageIndex = 0;
    this.applyFilter();
  }
  get activeCount(): number {
    return this.items.filter((d) => d.isActive !== false && !d.revokedAt).length;
  }
  get pairedCount(): number {
    return this.items.filter((d) => d.isPaired).length;
  }

  constructor(private http: HttpClient, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    this.load();
  }

  private api(path = ''): string {
    return `/devices/company/${this.companyId}/devices${path}`;
  }

  load(): void {
    if (!this.companyId) return;
    this.loading = true;
    this.http.get<KioskDeviceRow[]>(this.api()).subscribe({
      next: (rows) => {
        this.items = rows || [];
        this.applyFilter();
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        swal('Error', 'โหลดอุปกรณ์ไม่สำเร็จ', 'error');
      },
    });
  }

  applyFilter(): void {
    const q = (this._searchTerm || '').trim().toLowerCase();
    this.filtered = !q
      ? [...this.items]
      : this.items.filter((x) =>
          [x.name, x.locationLabel, x.stationMode, x.appVersion, x.fingerprint, x.deviceId]
            .join(' ')
            .toLowerCase()
            .includes(q)
        );
    const maxPage = Math.max(0, Math.ceil(this.filtered.length / this.pageSize) - 1);
    if (this.pageIndex > maxPage) this.pageIndex = maxPage;
    const start = this.pageIndex * this.pageSize;
    this.pageItems = this.filtered.slice(start, start + this.pageSize);
  }

  onPageChange(page: number): void {
    this.pageIndex = page;
    this.applyFilter();
  }

  clearSearch(): void {
    this.searchTerm = '';
  }

  openCreate(): void {
    this.detailOpen = false;
    this.createOpen = true;
  }

  openDetail(device: KioskDeviceRow): void {
    this.createOpen = false;
    this.selected = device;
    this.detailOpen = true;
  }

  create(): void {
    const name = (this.draft.name || '').trim();
    if (!name) {
      swal('ข้อมูลไม่ครบ', 'กรุณากรอกชื่ออุปกรณ์', 'warning');
      return;
    }
    this.http
      .post<KioskDeviceRow>(this.api(), {
        name,
        locationLabel: this.draft.locationLabel || null,
        stationMode: this.draft.stationMode || null,
        zoneId: this.draft.zoneId || null,
        appVersion: this.draft.appVersion || null,
      })
      .subscribe({
        next: (row) => {
          this.lastPairingCode = row.pairingCode || '';
          this.draft = { name: '', locationLabel: '', stationMode: 'ATTENDANCE', zoneId: '', appVersion: '' };
          this.createOpen = false;
          swal(
            'สร้างอุปกรณ์แล้ว',
            this.lastPairingCode
              ? `รหัสจับคู่ (แสดงครั้งเดียว): ${this.lastPairingCode}`
              : 'บันทึกแล้ว',
            'success'
          );
          this.load();
        },
        error: (err) =>
          swal('Error', err?.error?.detail || 'สร้างอุปกรณ์ไม่สำเร็จ', 'error'),
      });
  }

  rotate(device: KioskDeviceRow): void {
    swal({
      title: 'หมุนเวียนโทเคน / ออกโค้ดใหม่?',
      text: device.name,
      icon: 'warning',
      buttons: ['ยกเลิก', 'ยืนยัน'],
    }).then((ok: unknown) => {
      if (!ok) return;
      this.http.post<KioskDeviceRow>(this.api(`/${device.deviceId}/rotate`), {}).subscribe({
        next: (row) => {
          this.lastPairingCode = row.pairingCode || '';
          swal('หมุนเวียนแล้ว', `รหัสจับคู่ใหม่: ${this.lastPairingCode}`, 'success');
          this.load();
        },
        error: (err) => swal('Error', err?.error?.detail || 'หมุนเวียนไม่สำเร็จ', 'error'),
      });
    });
  }

  revoke(device: KioskDeviceRow): void {
    swal({
      title: 'เพิกถอนอุปกรณ์นี้?',
      text: device.name,
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'เพิกถอน'],
    }).then((ok: unknown) => {
      if (!ok) return;
      this.http.delete(this.api(`/${device.deviceId}`)).subscribe({
        next: () => {
          swal('สำเร็จ', 'เพิกถอนแล้ว', 'success');
          this.load();
        },
        error: () => swal('Error', 'เพิกถอนไม่สำเร็จ', 'error'),
      });
    });
  }

  saveBinding(device: KioskDeviceRow): void {
    this.http
      .patch(this.api(`/${device.deviceId}`), {
        stationMode: device.stationMode || null,
        zoneId: device.zoneId || null,
        locationLabel: device.locationLabel || null,
        name: device.name,
      })
      .subscribe({
        next: () => swal('สำเร็จ', 'บันทึกการผูกโหมดแล้ว', 'success'),
        error: (err) => swal('Error', err?.error?.detail || 'บันทึกไม่สำเร็จ', 'error'),
      });
  }

  refreshConfig(device: KioskDeviceRow): void {
    this.http
      .patch(this.api(`/${device.deviceId}`), {
        config: {
          ...(device.config || {}),
          remoteCommand: 'REFRESH_CONFIG',
          commandAt: new Date().toISOString(),
        },
      })
      .subscribe({
        next: () => swal('ส่งคำสั่งแล้ว', `ส่งคำสั่ง Refresh Config ไปยัง ${device.name} แล้ว`, 'success'),
        error: (err) => swal('Error', err?.error?.detail || 'ส่งคำสั่งไม่สำเร็จ', 'error'),
      });
  }

  copyKioskUrl(device: KioskDeviceRow): void {
    const mode = (device.stationMode || 'ATTENDANCE').toLowerCase().replace(/_/g, '-');
    const params = new URLSearchParams({ deviceId: device.deviceId });
    if (device.zoneId) params.set('zoneId', device.zoneId);
    const url = `${window.location.origin}/#/company/scan/${mode}?${params.toString()}`;
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(url).then(
        () => swal('คัดลอกลิงก์แล้ว', url, 'success'),
        () => swal('ลิงก์ Kiosk', url, 'info'),
      );
      return;
    }
    swal('ลิงก์ Kiosk', url, 'info');
  }

  statusLabel(d: KioskDeviceRow): string {
    if (d.revokedAt) return 'REVOKED';
    if (d.isPaired) return 'PAIRED';
    if (d.pairingPending) return 'PENDING';
    return 'NEW';
  }
}
