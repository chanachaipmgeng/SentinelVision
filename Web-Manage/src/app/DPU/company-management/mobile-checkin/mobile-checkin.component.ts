import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import swal from '../../../shared/utils/vault-swal';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';

@Component({
  selector: 'app-mobile-checkin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SharedModule],
  template: `
    <app-page-header [title]="'เช็กอินนอกสถานที่'" [activeTitle]="'Mobile Field Check-In'" [title1]="'GPS & Photo'"></app-page-header>
    <div class="max-w-xl mx-auto p-4 sm:p-6">
      <div class="box modern-card glass card-surface p-5 space-y-4">
        <div class="flex items-center justify-between">
          <h5 class="font-bold text-slate-100 mb-0 flex items-center gap-2">
            <i class="ri-map-pin-user-line text-cyan-400"></i> Mobile Field Check-In
          </h5>
          <a routerLink="/company/self-service" class="text-xs text-cyan-300 hover:underline">
            <i class="ri-arrow-left-line"></i> กลับ Self-Service
          </a>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <button
            type="button"
            class="py-2.5 rounded-lg border text-sm font-semibold transition"
            [ngClass]="timestampType === 1 ? 'bg-emerald-500/20 border-emerald-400 text-emerald-200' : 'bg-white/5 border-white/10 text-slate-300'"
            (click)="timestampType = 1"
          >
            <i class="ri-login-box-line me-1"></i> เข้างาน (Check-In)
          </button>
          <button
            type="button"
            class="py-2.5 rounded-lg border text-sm font-semibold transition"
            [ngClass]="timestampType === 2 ? 'bg-amber-500/20 border-amber-400 text-amber-200' : 'bg-white/5 border-white/10 text-slate-300'"
            (click)="timestampType = 2"
          >
            <i class="ri-logout-box-line me-1"></i> ออกงาน (Check-Out)
          </button>
        </div>

        <div class="p-3 rounded-lg bg-slate-950/60 border border-white/10 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-300">พิกัด GPS & ความแม่นยำ</span>
            <button type="button" class="ti-btn ti-btn-sm ti-btn-light text-xs" (click)="locateMe()">
              <i class="ri-crosshair-2-line me-1"></i> ดึงพิกัดปัจจุบัน
            </button>
          </div>
          <div class="grid grid-cols-3 gap-2 text-xs">
            <div>
              <label class="form-label text-[11px]">Latitude</label>
              <input type="number" step="0.000001" class="form-control form-control-sm" [(ngModel)]="latitude" />
            </div>
            <div>
              <label class="form-label text-[11px]">Longitude</label>
              <input type="number" step="0.000001" class="form-control form-control-sm" [(ngModel)]="longitude" />
            </div>
            <div>
              <label class="form-label text-[11px]">Accuracy (m)</label>
              <input type="number" class="form-control form-control-sm" [(ngModel)]="gpsAccuracy" />
            </div>
          </div>
          <div *ngIf="gpsStatusMsg" class="text-xs text-cyan-300">{{ gpsStatusMsg }}</div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="form-label">สถานที่ปฏิบัติงาน</label>
            <input type="text" class="form-control" [(ngModel)]="locationName" placeholder="เช่น ไซต์งานลูกค้า / นอกสถานที่" />
          </div>
          <div>
            <label class="form-label">Wi-Fi SSID / BSSID (ถ้ามี)</label>
            <input type="text" class="form-control" [(ngModel)]="wifiSsid" placeholder="ชื่อ Wi-Fi / BSSID" />
          </div>
        </div>

        <div>
          <label class="form-label">ถ่ายภาพ / แนบภาพหน้างาน</label>
          <label class="flex items-center justify-center gap-2 w-full px-4 py-3 rounded-lg border border-dashed border-cyan-500/40 bg-cyan-500/5 hover:bg-cyan-500/15 text-cyan-300 text-xs font-medium cursor-pointer transition">
            <i class="ri-camera-line text-base"></i>
            <span>{{ photoPreview ? 'เปลี่ยนภาพหน้างาน' : 'ถ่ายภาพ / เลือกไฟล์รูปภาพ' }}</span>
            <input type="file" accept="image/*" capture="user" class="hidden" (change)="onFileSelected($event)" />
          </label>
          <img *ngIf="photoPreview" [src]="photoPreview" alt="Preview" class="mt-2 rounded-lg max-h-48 object-cover border border-white/10" />
        </div>

        <div>
          <label class="form-label">หมายเหตุ</label>
          <textarea class="form-control" rows="2" [(ngModel)]="note" placeholder="รายละเอียดงานนอกสถานที่"></textarea>
        </div>

        <button type="button" class="btn-vault w-full py-3 rounded-lg font-semibold text-sm" [disabled]="submitting" (click)="submit()">
          <i class="ri-send-plane-fill me-1"></i> {{ submitting ? 'กำลังส่งข้อมูล...' : 'ยืนยันลงเวลานอกสถานที่' }}
        </button>

        <div
          *ngIf="lastResult"
          class="p-3 rounded-lg border text-xs"
          [ngClass]="lastResult.isMockGps ? 'bg-rose-500/15 border-rose-500/40 text-rose-200' : 'bg-emerald-500/15 border-emerald-500/40 text-emerald-200'"
        >
          <div class="font-bold">
            {{ lastResult.isMockGps ? 'ตรวจพบความผิดปกติ GPS (ถูกส่งเข้าคิวตรวจสอบ #08)' : 'บันทึกเวลาสำเร็จ' }}
          </div>
          <div *ngIf="lastResult.gpsIntegrityFlag">Flag: {{ lastResult.gpsIntegrityFlag }}</div>
        </div>
      </div>
    </div>
  `,
})
export class MobileCheckinComponent implements OnInit {
  companyId = '';
  timestampType = 1;
  latitude = 13.7563;
  longitude = 100.5018;
  gpsAccuracy: number | null = 20;
  locationName = 'Mobile Field Check-In';
  wifiSsid = '';
  wifiBssid = '';
  note = '';
  photoPreview = '';
  gpsStatusMsg = '';
  submitting = false;
  lastResult: { status?: string; isMockGps?: boolean; gpsIntegrityFlag?: string } | null = null;

  constructor(private http: HttpClient, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    this.locateMe();
  }

  locateMe(): void {
    if (!navigator.geolocation) {
      this.gpsStatusMsg = 'อุปกรณ์ไม่รองรับ Geolocation API';
      return;
    }
    this.gpsStatusMsg = 'กำลังอ่านพิกัด GPS...';
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.latitude = Number(pos.coords.latitude.toFixed(6));
        this.longitude = Number(pos.coords.longitude.toFixed(6));
        this.gpsAccuracy = Math.round(pos.coords.accuracy || 0);
        this.gpsStatusMsg = `อ่านพิกัดสำเร็จ (±${this.gpsAccuracy} ม.)`;
      },
      (err) => {
        this.gpsStatusMsg = `ไม่สามารถดึงพิกัดอัตโนมัติ (${err.message})`;
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      this.photoPreview = String(reader.result || '');
    };
    reader.readAsDataURL(file);
  }

  submit(): void {
    if (!this.companyId) return;
    this.submitting = true;
    this.http
      .post<{ status?: string; isMockGps?: boolean; gpsIntegrityFlag?: string }>(
        `/timestamp/company/${this.companyId}/mobile-checkin`,
        {
          timestampType: this.timestampType,
          latitude: Number(this.latitude),
          longitude: Number(this.longitude),
          gpsAccuracy: this.gpsAccuracy !== null ? Number(this.gpsAccuracy) : null,
          locationName: this.locationName,
          wifiSsid: this.wifiSsid || null,
          wifiBssid: this.wifiBssid || null,
          photoTimestamp: this.photoPreview || null,
          note: this.note,
        }
      )
      .subscribe({
        next: (res) => {
          this.submitting = false;
          this.lastResult = res;
          if (res?.isMockGps) {
            swal('แจ้งเตือน GPS', `ระบบตรวจพบความผิดปกติ: ${res.gpsIntegrityFlag}`, 'warning');
          } else {
            swal('สำเร็จ', 'บันทึกการลงเวลานอกสถานที่เรียบร้อย', 'success');
          }
        },
        error: (err) => {
          this.submitting = false;
          swal('Error', err?.error?.detail || 'ลงเวลาไม่สำเร็จ', 'error');
        },
      });
  }
}
