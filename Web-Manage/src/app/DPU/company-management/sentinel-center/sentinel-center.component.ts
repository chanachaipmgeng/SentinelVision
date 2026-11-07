import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';

/** Legacy ?tab= values → dedicated module routes. */
const LEGACY_TAB_REDIRECTS: Record<string, string> = {
  command: '/company/scan-hub',
  watchlist: '/company/watchlist/identities',
  access: '/company/access-control/zones',
  visitors: '/company/visitors/passes',
  events: '/company/events/campaigns',
  muster: '/company/visitors/muster-roll',
};

type SentinelTab = 'command' | 'watchlist' | 'access' | 'visitors' | 'events' | 'muster';

/** Map `/company/{module}/:section` → active sentinel tab. */
function tabFromModuleSection(
  workspace: string | null | undefined,
  section: string | null | undefined
): SentinelTab | null {
  if (!workspace) return null;
  switch (workspace) {
    case 'ACCESS_CONTROL':
      return 'access';
    case 'WATCHLIST':
      return 'watchlist';
    case 'VISITOR':
      return section === 'muster-roll' ? 'muster' : 'visitors';
    case 'EVENTS':
      return 'events';
    default:
      return null;
  }
}

@Component({
  selector: 'app-sentinel-center',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SharedModule],
  template: `
    <app-page-header
      [title]="'SentinelVision — ศูนย์ควบคุมอัตลักษณ์ ความปลอดภัย Access Control & Smart Events'"
      [activeTitle]="'SentinelVision Command'"
      [title1]="'Security, Access, Watchlist & Events'"
    ></app-page-header>

    <div class="space-y-6">
      <!-- Hero Command Banner -->
      <div class="sv-command-banner flex flex-wrap items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2 text-xs uppercase tracking-wider opacity-80 mb-1">
            <i class="ri-shield-flash-line text-base"></i>
            <span>SentinelVision Unified Biometric Platform • InsightFace 512-d HNSW</span>
          </div>
          <h4 class="text-xl font-bold text-white mb-1">
            ศูนย์ปฏิบัติการยืนยันตัวตน เฝ้าระวังความปลอดภัย และควบคุมการเข้า-ออกอัจฉริยะ
          </h4>
          <p class="text-xs text-white/80 mb-0">
            เชื่อมโยงระบบลงเวลาพนักงาน, บัญชีเฝ้าระวัง (Blacklist/VIP), ประตู Access Control, ผู้มาติดต่อ (Visitor Pass), และงานอีเวนต์ในสมองกลเดียว
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <a
            routerLink="/company/timestamp-face"
            class="ti-btn bg-white text-slate-900 hover:bg-slate-100 font-semibold text-xs px-3.5 py-2 rounded-lg"
          >
            <i class="ri-camera-lens-line me-1"></i> เปิดหน้าจอ Kiosk สด
          </a>
          <button
            type="button"
            class="ti-btn bg-teal-500/20 border border-white/25 text-white hover:bg-teal-500/30 text-xs px-3.5 py-2 rounded-lg"
            (click)="reloadAll()"
          >
            <i class="ri-refresh-line me-1" [class.animate-spin]="isLoading"></i> รีเฟรชข้อมูล
          </button>
        </div>
      </div>

      <!-- KPI Overview Row -->
      <div class="grid grid-cols-12 gap-4 sv-contain-region">
        <div class="col-span-6 md:col-span-4 xl:col-span-2">
          <div class="sv-kpi-card">
            <div class="flex items-center justify-between text-xs text-dpu-muted mb-1">
              <span>Blacklist / เฝ้าระวัง</span>
              <i class="ri-alarm-warning-line text-danger text-base"></i>
            </div>
            <div class="text-2xl font-bold text-danger">
              {{ overview?.summary?.blacklistAndPoiCount || 0 }}
            </div>
            <div class="text-[0.72rem] text-dpu-muted mt-1">แจ้งเตือนเงียบอัตโนมัติ</div>
          </div>
        </div>

        <div class="col-span-6 md:col-span-4 xl:col-span-2">
          <div class="sv-kpi-card">
            <div class="flex items-center justify-between text-xs text-dpu-muted mb-1">
              <span>บุคคลสำคัญ (VIP)</span>
              <i class="ri-vip-crown-line text-purple-600 text-base"></i>
            </div>
            <div class="text-2xl font-bold text-purple-700">
              {{ overview?.summary?.vipCount || 0 }}
            </div>
            <div class="text-[0.72rem] text-dpu-muted mt-1">ต้อนรับพิเศษที่จุดสแกน</div>
          </div>
        </div>

        <div class="col-span-6 md:col-span-4 xl:col-span-2">
          <div class="sv-kpi-card">
            <div class="flex items-center justify-between text-xs text-dpu-muted mb-1">
              <span>ผู้มาติดต่อ (Visitor)</span>
              <i class="ri-pass-valid-line text-sky-600 text-base"></i>
            </div>
            <div class="text-2xl font-bold text-sky-700">
              {{ overview?.summary?.activeVisitorCount || 0 }}
            </div>
            <div class="text-[0.72rem] text-dpu-muted mt-1">ลบใบหน้าอัตโนมัติตาม PDPA</div>
          </div>
        </div>

        <div class="col-span-6 md:col-span-4 xl:col-span-2">
          <div class="sv-kpi-card">
            <div class="flex items-center justify-between text-xs text-dpu-muted mb-1">
              <span>โซนประตู Access</span>
              <i class="ri-door-lock-box-line text-teal-600 text-base"></i>
            </div>
            <div class="text-2xl font-bold text-dpu-brand-deep">
              {{ overview?.summary?.activeZonesCount || 0 }}
            </div>
            <div class="text-[0.72rem] text-dpu-muted mt-1">รองรับ IoT Relay &amp; 2FA</div>
          </div>
        </div>

        <div class="col-span-6 md:col-span-4 xl:col-span-2">
          <div class="sv-kpi-card">
            <div class="flex items-center justify-between text-xs text-dpu-muted mb-1">
              <span>งานอีเวนต์ / สัมมนา</span>
              <i class="ri-calendar-event-line text-amber-600 text-base"></i>
            </div>
            <div class="text-2xl font-bold text-amber-700">
              {{ overview?.summary?.liveEventsCount || 0 }}
            </div>
            <div class="text-[0.72rem] text-dpu-muted mt-1">
              ผู้ลงทะเบียน {{ overview?.summary?.eventAttendeeCount || 0 }} คน
            </div>
          </div>
        </div>

        <div class="col-span-6 md:col-span-4 xl:col-span-2">
          <div class="sv-kpi-card">
            <div class="flex items-center justify-between text-xs text-dpu-muted mb-1">
              <span>คนในอาคารวันนี้</span>
              <i class="ri-building-2-line text-emerald-600 text-base"></i>
            </div>
            <div class="text-2xl font-bold text-emerald-700">
              {{ overview?.summary?.buildingOccupancyCount || 0 }}
            </div>
            <div class="text-[0.72rem] text-dpu-muted mt-1">
              ค้างตรวจสอบ {{ overview?.summary?.unacknowledgedAlerts || 0 }} เหตุการณ์
            </div>
          </div>
        </div>
      </div>

      <!-- Navigation Workspace Tabs -->
      <div class="box modern-card glass">
        <div class="box-header flex flex-wrap items-center justify-between gap-3">
          <nav
            *ngIf="!moduleScoped"
            class="sv-nav-tabs"
            aria-label="SentinelVision Workspaces"
          >
            <button
              type="button"
              class="sv-nav-tab"
              [class.sv-nav-tab--active]="activeTab === 'command'"
              (click)="setTab('command')"
            >
              <i class="ri-radar-line"></i>
              <span>ศูนย์เฝ้าระวัง &amp; ทดสอบสแกน 1:N</span>
            </button>
            <button
              type="button"
              class="sv-nav-tab"
              [class.sv-nav-tab--active]="activeTab === 'watchlist'"
              (click)="setTab('watchlist')"
            >
              <i class="ri-shield-user-line"></i>
              <span>Watchlist / Blacklist &amp; VIP</span>
            </button>
            <button
              type="button"
              class="sv-nav-tab"
              [class.sv-nav-tab--active]="activeTab === 'access'"
              (click)="setTab('access')"
            >
              <i class="ri-door-lock-line"></i>
              <span>Access Control &amp; โซนประตู</span>
            </button>
            <button
              type="button"
              class="sv-nav-tab"
              [class.sv-nav-tab--active]="activeTab === 'visitors'"
              (click)="setTab('visitors')"
            >
              <i class="ri-user-shared-line"></i>
              <span>ผู้มาติดต่อ (Visitor Pass)</span>
            </button>
            <button
              type="button"
              class="sv-nav-tab"
              [class.sv-nav-tab--active]="activeTab === 'events'"
              (click)="setTab('events')"
            >
              <i class="ri-ticket-2-line"></i>
              <span>งานอีเวนต์ &amp; สัมมนา</span>
            </button>
            <button
              type="button"
              class="sv-nav-tab"
              [class.sv-nav-tab--active]="activeTab === 'muster'"
              (click)="setTab('muster')"
            >
              <i class="ri-Broadcast-line"></i>
              <span>เช็คยอดคนในอาคาร &amp; Edge AI</span>
            </button>
          </nav>
          <div *ngIf="moduleScoped" class="text-sm font-semibold text-slate-700">
            {{ moduleWorkspaceLabel }}
          </div>

          <span
            *ngIf="toastMessage"
            class="badge bg-teal-600/10 text-teal-800 border border-teal-600/20 px-3 py-1.5 text-xs font-semibold"
          >
            <i class="ri-checkbox-circle-line me-1"></i> {{ toastMessage }}
          </span>
        </div>

        <!-- ================================================================
             TAB 1: SECURITY COMMAND & UNIFIED 1:N SCAN SIMULATOR
             ================================================================ -->
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'command'">
          <div class="grid grid-cols-12 gap-6">
            <!-- Unified 1:N Biometric Scan Verifier -->
            <div class="col-span-12 xl:col-span-5 p-5 rounded-xl border border-defaultborder bg-slate-50/60">
              <div class="flex items-center justify-between mb-3">
                <div>
                  <h6 class="font-bold text-base mb-0">
                    <i class="ri-scan-2-line text-teal-700 me-1"></i>
                    ทดสอบสแกนใบหน้าอัจฉริยะ 1:N (Unified Scan Engine)
                  </h6>
                  <p class="text-xs text-dpu-muted mb-0">
                    ตรวจสอบพร้อมกันทั้ง พนักงาน, Blacklist, VIP, Visitor และผู้ร่วมงาน Event
                  </p>
                </div>
              </div>

              <div class="grid grid-cols-12 gap-3">
                <div class="col-span-12 sm:col-span-6">
                  <label class="form-label text-xs font-semibold">โหมดจุดสแกน (Station Mode)</label>
                  <select class="form-control" [(ngModel)]="scanForm.stationMode">
                    <option value="ACCESS_CONTROL">Access Control (ควบคุมประตู)</option>
                    <option value="WATCHLIST_MONITOR">Watchlist Monitor (กล้องเฝ้าระวัง)</option>
                    <option value="EVENT_CHECKIN">Event Check-in (ลงทะเบียนเข้างาน)</option>
                    <option value="ATTENDANCE">Attendance (ลงเวลาทำงาน)</option>
                  </select>
                </div>
                <div class="col-span-12 sm:col-span-6">
                  <label class="form-label text-xs font-semibold">โซนประตู (Access Zone)</label>
                  <select class="form-control" [(ngModel)]="scanForm.zoneId">
                    <option value="">-- ไม่ระบุโซน (ตรวจสอบทั่วไป) --</option>
                    <option *ngFor="let z of zones" [value]="z.zoneId">
                      {{ z.name }} ({{ z.code }})
                    </option>
                  </select>
                </div>
                <div class="col-span-12 sm:col-span-6">
                  <label class="form-label text-xs font-semibold">แคมเปญงานอีเวนต์ (ถ้ามี)</label>
                  <select class="form-control" [(ngModel)]="scanForm.eventId">
                    <option value="">-- ไม่ระบุงานอีเวนต์ --</option>
                    <option *ngFor="let ev of events" [value]="ev.eventId">
                      {{ ev.name }}
                    </option>
                  </select>
                </div>
                <div class="col-span-12 sm:col-span-6">
                  <label class="form-label text-xs font-semibold">รหัส 2FA / PIN (สำหรับโซนความมั่นคงสูง)</label>
                  <input
                    type="text"
                    class="form-control"
                    [(ngModel)]="scanForm.totpOrPin"
                    placeholder="เว้นว่างได้หากโซนไม่บังคับ 2FA"
                  />
                </div>
                <div class="col-span-12">
                  <label class="form-label text-xs font-semibold">เลือกรูปภาพใบหน้าเพื่อจำลองการสแกนหน้า Kiosk/กล้อง</label>
                  <input
                    type="file"
                    accept="image/*"
                    class="form-control"
                    (change)="onScanFileSelected($event)"
                  />
                </div>
                <div class="col-span-12">
                  <button
                    type="button"
                    class="ti-btn ti-btn-primary-full w-full font-semibold"
                    [disabled]="!scanSelectedFile || isScanning"
                    (click)="runUnifiedScan()"
                  >
                    <i class="ri-qr-scan-2-line me-1"></i>
                    {{ isScanning ? 'กำลังประมวลผลด้วย InsightFace GPU...' : 'เริ่มตรวจสอบใบหน้า 1:N ทันที' }}
                  </button>
                </div>
              </div>

              <!-- Scan Result Box -->
              <div
                *ngIf="lastScanResult"
                class="mt-4 p-4 rounded-xl border"
                [ngClass]="
                  lastScanResult.decision === 'BLACKLIST_BLOCKED'
                    ? 'bg-red-50 border-red-300 text-red-900'
                    : lastScanResult.accessGranted
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
                    : 'bg-amber-50 border-amber-300 text-amber-900'
                "
              >
                <div class="flex items-center justify-between mb-1">
                  <span class="font-bold text-sm">
                    {{ lastScanResult.message }}
                  </span>
                  <span class="badge bg-white/80 text-slate-800 px-2 py-0.5 text-xs">
                    {{ lastScanResult.decision }}
                  </span>
                </div>
                <div class="text-xs space-y-1 opacity-90">
                  <div *ngIf="lastScanResult.subjectName">
                    <strong>ชื่อ-นามสกุล:</strong> {{ lastScanResult.subjectName }} ({{ lastScanResult.identityType }})
                  </div>
                  <div *ngIf="lastScanResult.confidencePercent != null">
                    <strong>ความแม่นยำ (Confidence):</strong> {{ lastScanResult.confidencePercent }}%
                  </div>
                  <div *ngIf="lastScanResult.seatNumber">
                    <strong>ที่นั่ง / โต๊ะงานอีเวนต์:</strong> {{ lastScanResult.seatNumber }}
                  </div>
                  <div *ngIf="lastScanResult.alertNote">
                    <strong>หมายเหตุเฝ้าระวัง:</strong> {{ lastScanResult.alertNote }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Live Security Incident Log -->
            <div class="col-span-12 xl:col-span-7">
              <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div>
                  <h6 class="font-bold text-base mb-0">
                    รายการแจ้งเตือนความปลอดภัยและการเข้า-ออกล่าสุด (Security &amp; Access Feed)
                  </h6>
                  <p class="text-xs text-dpu-muted mb-0">
                    บันทึกทุกเหตุการณ์ Blacklist, VIP, ประตู Access Control และการเช็คอินงานอีเวนต์
                  </p>
                </div>
                <div class="flex items-center gap-2">
                  <select class="form-control !py-1 !text-xs !w-auto" [(ngModel)]="incidentFilterSeverity" (change)="loadIncidents()">
                    <option value="">ทุกระดับความสำคัญ</option>
                    <option value="CRITICAL">CRITICAL (ฉุกเฉิน/Blacklist)</option>
                    <option value="WARNING">WARNING (ปฏิเสธสิทธิ์)</option>
                    <option value="INFO">INFO (ผ่านปกติ/VIP)</option>
                  </select>
                </div>
              </div>

              <div
                tabindex="0"
                role="region"
                aria-label="ตารางเหตุการณ์ความปลอดภัยและการเข้า-ออก"
                class="sv-table-wrapper"
              >
                <table class="table whitespace-nowrap">
                  <thead>
                    <tr class="border-b border-defaultborder text-xs">
                      <th class="text-start p-3">บุคคล / ตัวตน</th>
                      <th class="text-start p-3">ประเภทเหตุการณ์</th>
                      <th class="text-start p-3">จุดสแกน / โซน</th>
                      <th class="text-start p-3">ความแม่นยำ</th>
                      <th class="text-start p-3">เวลา</th>
                      <th class="text-end p-3">สถานะ</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let inc of incidents" class="border-b border-defaultborder text-xs">
                      <th class="text-start p-3">
                        <div class="font-semibold text-slate-900">{{ inc.subjectName || 'Unknown' }}</div>
                        <div class="text-[0.7rem] text-dpu-muted">{{ inc.identityType || '-' }}</div>
                      </th>
                      <td class="p-3">
                        <span
                          class="badge px-2 py-0.5 rounded"
                          [ngClass]="
                            inc.severity === 'CRITICAL'
                              ? 'sv-pill-critical'
                              : inc.severity === 'WARNING'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-emerald-100 text-emerald-800'
                          "
                        >
                          {{ inc.eventType }}
                        </span>
                        <div class="text-[0.7rem] text-dpu-muted mt-0.5">{{ inc.actionTaken }}</div>
                      </td>
                      <td class="p-3">{{ inc.zoneName || '-' }}</td>
                      <td class="p-3">
                        <span *ngIf="inc.confidencePercent != null">{{ inc.confidencePercent }}%</span>
                        <span *ngIf="inc.confidencePercent == null" class="text-dpu-muted">-</span>
                      </td>
                      <td class="p-3">{{ inc.occurredAt | date:'dd/MM HH:mm:ss' }}</td>
                      <td class="p-3 text-end">
                        <button
                          *ngIf="!inc.acknowledgedAt && (inc.severity === 'CRITICAL' || inc.severity === 'WARNING')"
                          type="button"
                          class="ti-btn ti-btn-sm ti-btn-primary-full"
                          (click)="acknowledgeIncident(inc.incidentId)"
                        >
                          รับทราบเหตุ
                        </button>
                        <span *ngIf="inc.acknowledgedAt" class="text-[0.7rem] text-emerald-700 font-semibold">
                          รับทราบแล้ว
                        </span>
                      </td>
                    </tr>
                    <tr *ngIf="incidents.length === 0">
                      <td colspan="6" class="text-center text-dpu-muted py-6">
                        ยังไม่มีเหตุการณ์แจ้งเตือนในหมวดนี้
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- ================================================================
             TAB 2: WATCHLIST, BLACKLIST & VIP REGISTRY
             ================================================================ -->
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'watchlist'">
          <div class="grid grid-cols-12 gap-6">
            <div class="col-span-12 lg:col-span-4 p-5 rounded-xl border border-defaultborder bg-slate-50/60">
              <h6 class="font-bold text-base mb-1">
                ขึ้นทะเบียนบัญชีเฝ้าระวัง (Blacklist / POI) หรือบุคคลสำคัญ (VIP)
              </h6>
              <p class="text-xs text-dpu-muted mb-4">
                เมื่อกล้อง Kiosk ตรวจพบใบหน้าในกลุ่มนี้ ระบบจะแจ้งเตือนไปยังเจ้าหน้าที่ทันที
              </p>

              <div class="grid grid-cols-12 gap-3">
                <div class="col-span-12 sm:col-span-6">
                  <label class="form-label text-xs font-semibold">หมวดหมู่บัญชี</label>
                  <select class="form-control" [(ngModel)]="watchlistForm.identityType">
                    <option value="BLACKLIST">🔴 BLACKLIST (บุคคลต้องห้าม)</option>
                    <option value="POI">🟡 POI (บุคคลเฝ้าระวังพิเศษ)</option>
                    <option value="VIP">🟣 VIP (แขกผู้บริหาร/ต้อนรับพิเศษ)</option>
                  </select>
                </div>
                <div class="col-span-12 sm:col-span-6">
                  <label class="form-label text-xs font-semibold">ระดับความสำคัญ</label>
                  <select class="form-control" [(ngModel)]="watchlistForm.severity">
                    <option value="CRITICAL">CRITICAL (สูงสุด/แจ้งเตือนด่วน)</option>
                    <option value="HIGH">HIGH (สูง)</option>
                    <option value="MEDIUM">MEDIUM (ปานกลาง)</option>
                    <option value="LOW">LOW (ทั่วไป)</option>
                  </select>
                </div>
                <div class="col-span-12">
                  <label class="form-label text-xs font-semibold">ชื่อ - นามสกุล / ชื่อเรียก</label>
                  <input
                    class="form-control"
                    [(ngModel)]="watchlistForm.fullName"
                    placeholder="ระบุชื่อ-นามสกุล หรือรหัสอ้างอิง"
                  />
                </div>
                <div class="col-span-12 sm:col-span-6">
                  <label class="form-label text-xs font-semibold">เลขบัตร / พาสปอร์ต (ถ้ามี)</label>
                  <input class="form-control" [(ngModel)]="watchlistForm.documentRef" placeholder="เช่น ID / Passport" />
                </div>
                <div class="col-span-12 sm:col-span-6">
                  <label class="form-label text-xs font-semibold">หน่วยงาน / บริษัท</label>
                  <input class="form-control" [(ngModel)]="watchlistForm.organization" placeholder="ระบุสังกัด (ถ้ามี)" />
                </div>
                <div class="col-span-12">
                  <label class="form-label text-xs font-semibold">ข้อความแจ้งเตือน รปภ. / ฝ่ายต้อนรับ</label>
                  <textarea
                    rows="2"
                    class="form-control"
                    [(ngModel)]="watchlistForm.alertNote"
                    placeholder="เช่น ห้ามเข้าพื้นที่อาคาร B เด็ดขาด หรือ แจ้งเลขาผู้บริหารทันทีที่มาถึง"
                  ></textarea>
                </div>
                <div class="col-span-12">
                  <label class="form-label text-xs font-semibold">รูปถ่ายใบหน้า (สกัด Embedding 512-d อัตโนมัติ)</label>
                  <input
                    type="file"
                    accept="image/*"
                    class="form-control"
                    (change)="onIdentityPhotoSelected($event)"
                  />
                </div>
                <div class="col-span-12">
                  <button
                    type="button"
                    class="ti-btn ti-btn-primary-full w-full font-semibold"
                    (click)="createIdentityRecord(watchlistForm)"
                  >
                    + บันทึกรายชื่อเข้าสู่ระบบเฝ้าระวัง
                  </button>
                </div>
              </div>
            </div>

            <div class="col-span-12 lg:col-span-8">
              <h6 class="font-bold text-base mb-3">
                ทะเบียนรายชื่อ Watchlist / Blacklist &amp; VIP ({{ watchlistItems.length }})
              </h6>
              <div
                tabindex="0"
                role="region"
                aria-label="ตารางรายชื่อ Watchlist และ VIP"
                class="sv-table-wrapper"
              >
                <table class="table whitespace-nowrap">
                  <thead>
                    <tr class="border-b border-defaultborder text-xs">
                      <th class="text-start p-3">ชื่อ-นามสกุล</th>
                      <th class="text-start p-3">ประเภท</th>
                      <th class="text-start p-3">ระดับ</th>
                      <th class="text-start p-3">คำสั่งแจ้งเตือน</th>
                      <th class="text-start p-3">ข้อมูลใบหน้า 512-d</th>
                      <th class="text-end p-3">จัดการ</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let item of watchlistItems" class="border-b border-defaultborder text-xs">
                      <th class="text-start p-3">
                        <div class="font-semibold">{{ item.fullName }}</div>
                        <div class="text-[0.7rem] text-dpu-muted">{{ item.organization || item.documentRef || '-' }}</div>
                      </th>
                      <td class="p-3">
                        <span
                          class="badge px-2.5 py-0.5 rounded"
                          [ngClass]="item.identityType === 'VIP' ? 'sv-pill-vip' : 'sv-pill-critical'"
                        >
                          {{ item.identityType }}
                        </span>
                      </td>
                      <td class="p-3 font-semibold">{{ item.severity }}</td>
                      <td class="p-3 max-w-xs truncate" [title]="item.alertNote || ''">
                        {{ item.alertNote || '-' }}
                      </td>
                      <td class="p-3">
                        <span
                          *ngIf="item.hasFaceEnrolled"
                          class="badge bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded"
                        >
                          พร้อมสแกน 1:N
                        </span>
                        <label
                          *ngIf="!item.hasFaceEnrolled"
                          class="badge bg-amber-100 text-amber-800 px-2 py-0.5 rounded cursor-pointer"
                        >
                          + อัปโหลดใบหน้า
                          <input
                            type="file"
                            accept="image/*"
                            class="hidden"
                            (change)="enrollExistingIdentityFace(item.identityId, $event)"
                          />
                        </label>
                      </td>
                      <td class="p-3 text-end">
                        <button
                          type="button"
                          class="ti-btn ti-btn-sm ti-btn-danger"
                          (click)="deleteIdentity(item.identityId)"
                        >
                          ลบ
                        </button>
                      </td>
                    </tr>
                    <tr *ngIf="watchlistItems.length === 0">
                      <td colspan="6" class="text-center text-dpu-muted py-6">
                        ยังไม่มีรายชื่อในบัญชี Watchlist / Blacklist / VIP
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- ================================================================
             TAB 3: SMART ACCESS CONTROL & DOOR ZONES
             ================================================================ -->
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'access'">
          <div class="grid grid-cols-12 gap-6">
            <div class="col-span-12 lg:col-span-4 p-5 rounded-xl border border-defaultborder bg-slate-50/60">
              <h6 class="font-bold text-base mb-1">สร้างโซนควบคุมประตู / จุดสแกน (Access Zone)</h6>
              <p class="text-xs text-dpu-muted mb-4">
                กำหนดสิทธิ์การเข้าพื้นที่ ช่วงเวลาอนุญาต ระบบ 2FA และ Webhook สั่งเปิดกลอนประตูอัจฉริยะ
              </p>

              <div class="grid grid-cols-12 gap-3">
                <div class="col-span-12 sm:col-span-8">
                  <label class="form-label text-xs font-semibold">ชื่อประตู / โซนพื้นที่</label>
                  <input
                    class="form-control"
                    [(ngModel)]="zoneForm.name"
                    placeholder="เช่น ประตูห้อง Server ชั้น 4 / ประตูทางเข้าหลัก"
                  />
                </div>
                <div class="col-span-12 sm:col-span-4">
                  <label class="form-label text-xs font-semibold">รหัสประตู</label>
                  <input class="form-control" [(ngModel)]="zoneForm.code" placeholder="GATE-01" />
                </div>
                <div class="col-span-12">
                  <label class="form-label text-xs font-semibold">โหมดการทำงานหลัก</label>
                  <select class="form-control" [(ngModel)]="zoneForm.stationMode">
                    <option value="ACCESS_CONTROL">ACCESS_CONTROL (สแกนเปิดประตู)</option>
                    <option value="ATTENDANCE">ATTENDANCE (ลงเวลา + เปิดประตู)</option>
                    <option value="WATCHLIST_MONITOR">WATCHLIST_MONITOR (กล้องเฝ้าระวัง)</option>
                    <option value="EVENT_CHECKIN">EVENT_CHECKIN (จุดต้อนรับงานอีเวนต์)</option>
                  </select>
                </div>
                <div class="col-span-6">
                  <label class="form-label text-xs font-semibold">เวลาเริ่มอนุญาต</label>
                  <input type="time" class="form-control" [(ngModel)]="zoneForm.scheduleStart" />
                </div>
                <div class="col-span-6">
                  <label class="form-label text-xs font-semibold">เวลาสิ้นสุดอนุญาต</label>
                  <input type="time" class="form-control" [(ngModel)]="zoneForm.scheduleEnd" />
                </div>
                <div class="col-span-12">
                  <label class="form-label text-xs font-semibold">กลุ่มผู้มีสิทธิ์ผ่านประตู</label>
                  <div class="flex flex-wrap gap-3 text-xs mt-1">
                    <label class="flex items-center gap-1.5 cursor-pointer">
                      <input type="checkbox" [(ngModel)]="zoneForm.allowEmployee" />
                      <span>พนักงาน (EMPLOYEE)</span>
                    </label>
                    <label class="flex items-center gap-1.5 cursor-pointer">
                      <input type="checkbox" [(ngModel)]="zoneForm.allowVip" />
                      <span>แขก VIP</span>
                    </label>
                    <label class="flex items-center gap-1.5 cursor-pointer">
                      <input type="checkbox" [(ngModel)]="zoneForm.allowVisitor" />
                      <span>ผู้มาติดต่อ (VISITOR)</span>
                    </label>
                  </div>
                </div>
                <div class="col-span-12">
                  <label class="form-label text-xs font-semibold">IoT Door Relay Webhook URL (ถ้ามี)</label>
                  <input
                    class="form-control"
                    [(ngModel)]="zoneForm.relayWebhookUrl"
                    placeholder="https://iot-gateway.local/api/doors/gate-01/unlock"
                  />
                </div>
                <div class="col-span-12">
                  <label class="flex items-center gap-2 text-xs cursor-pointer">
                    <input type="checkbox" [(ngModel)]="zoneForm.require2FA" />
                    <span class="font-semibold text-teal-900">
                      บังคับยืนยันตัวตน 2 ชั้น (Face + PIN/TOTP) สำหรับโซนความมั่นคงสูง
                    </span>
                  </label>
                </div>
                <div class="col-span-12">
                  <button
                    type="button"
                    class="ti-btn ti-btn-primary-full w-full font-semibold"
                    (click)="createAccessZone()"
                  >
                    + บันทึกโซนควบคุมการเข้า-ออก
                  </button>
                </div>
              </div>
            </div>

            <div class="col-span-12 lg:col-span-8">
              <h6 class="font-bold text-base mb-3">
                รายการโซนประตูและจุดควบคุมทั้งหมด ({{ zones.length }})
              </h6>
              <div
                tabindex="0"
                role="region"
                aria-label="ตารางโซนประตู Access Control"
                class="sv-table-wrapper"
              >
                <table class="table whitespace-nowrap">
                  <thead>
                    <tr class="border-b border-defaultborder text-xs">
                      <th class="text-start p-3">ชื่อโซน / ประตู</th>
                      <th class="text-start p-3">โหมด</th>
                      <th class="text-start p-3">กลุ่มที่อนุญาต</th>
                      <th class="text-start p-3">เวลาเปิดสิทธิ์</th>
                      <th class="text-start p-3">ความปลอดภัย</th>
                      <th class="text-end p-3">สั่งการด่วน</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let z of zones" class="border-b border-defaultborder text-xs">
                      <th class="text-start p-3">
                        <div class="font-semibold">{{ z.name }}</div>
                        <div class="text-[0.7rem] text-dpu-muted">Code: {{ z.code }}</div>
                      </th>
                      <td class="p-3">
                        <span class="badge bg-slate-100 text-slate-800 px-2 py-0.5 rounded">
                          {{ z.stationMode }}
                        </span>
                      </td>
                      <td class="p-3">
                        <span
                          *ngFor="let t of z.allowedIdentityTypes"
                          class="badge bg-teal-50 text-teal-800 border border-teal-200 me-1 px-1.5 py-0.5 rounded"
                        >
                          {{ t }}
                        </span>
                      </td>
                      <td class="p-3">{{ z.scheduleStart }} - {{ z.scheduleEnd }}</td>
                      <td class="p-3">
                        <span *ngIf="z.require2FA" class="badge bg-amber-100 text-amber-800 px-2 py-0.5 rounded">
                          Face + 2FA
                        </span>
                        <span *ngIf="!z.require2FA" class="badge bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">
                          Face Single-Step
                        </span>
                      </td>
                      <td class="p-3 text-end space-x-1">
                        <button
                          type="button"
                          class="ti-btn ti-btn-sm ti-btn-primary-full"
                          (click)="remoteUnlockZone(z.zoneId)"
                        >
                          <i class="ri-lock-unlock-line me-1"></i> สั่งปลดล็อกประตู
                        </button>
                        <button
                          type="button"
                          class="ti-btn ti-btn-sm ti-btn-danger"
                          (click)="deleteZone(z.zoneId)"
                        >
                          ลบ
                        </button>
                      </td>
                    </tr>
                    <tr *ngIf="zones.length === 0">
                      <td colspan="6" class="text-center text-dpu-muted py-6">
                        ยังไม่มีโซนควบคุมประตู (สร้างโซนด้านซ้ายเพื่อเริ่มใช้งาน Access Control)
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- ================================================================
             TAB 4: VISITOR PASS & TEMPORARY BIOMETRICS
             ================================================================ -->
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'visitors'">
          <div class="grid grid-cols-12 gap-6">
            <div class="col-span-12 lg:col-span-4 p-5 rounded-xl border border-defaultborder bg-slate-50/60">
              <h6 class="font-bold text-base mb-1">ลงทะเบียนผู้มาติดต่อชั่วคราว (Visitor Face Pass)</h6>
              <p class="text-xs text-dpu-muted mb-4">
                อนุญาตให้ผู้มาติดต่อเดินสแกนใบหน้าผ่านประตูที่กำหนด และหมดอายุพร้อมลบข้อมูลอัตโนมัติตาม PDPA
              </p>

              <div class="grid grid-cols-12 gap-3">
                <div class="col-span-12">
                  <label class="form-label text-xs font-semibold">ชื่อ - นามสกุล ผู้มาติดต่อ</label>
                  <input
                    class="form-control"
                    [(ngModel)]="visitorForm.fullName"
                    placeholder="เช่น คุณสมชาย ใจดี"
                  />
                </div>
                <div class="col-span-12 sm:col-span-6">
                  <label class="form-label text-xs font-semibold">บริษัท / หน่วยงาน</label>
                  <input class="form-control" [(ngModel)]="visitorForm.organization" placeholder="บริษัทคู่ค้า / ผู้รับเหมา" />
                </div>
                <div class="col-span-12 sm:col-span-6">
                  <label class="form-label text-xs font-semibold">เบอร์โทรศัพท์</label>
                  <input class="form-control" [(ngModel)]="visitorForm.phoneNumber" placeholder="08x-xxx-xxxx" />
                </div>
                <div class="col-span-12">
                  <label class="form-label text-xs font-semibold">วัตถุประสงค์การเข้าติดต่อ</label>
                  <input
                    class="form-control"
                    [(ngModel)]="visitorForm.visitPurpose"
                    placeholder="เช่น ประชุมโปรเจกต์ชั้น 3 / ซ่อมบำรุงระบบแอร์"
                  />
                </div>
                <div class="col-span-12">
                  <label class="form-label text-xs font-semibold">เวลาหมดอายุบัตรใบหน้าอัตโนมัติ (PDPA Expiry)</label>
                  <input type="datetime-local" class="form-control" [(ngModel)]="visitorForm.expiresAt" />
                </div>
                <div class="col-span-12">
                  <label class="form-label text-xs font-semibold">รูปถ่ายใบหน้าผู้มาติดต่อ</label>
                  <input
                    type="file"
                    accept="image/*"
                    class="form-control"
                    (change)="onIdentityPhotoSelected($event)"
                  />
                </div>
                <div class="col-span-12">
                  <button
                    type="button"
                    class="ti-btn ti-btn-primary-full w-full font-semibold"
                    (click)="createIdentityRecord(visitorForm)"
                  >
                    + ออกบัตรผ่านใบหน้าชั่วคราว (Issue Visitor Pass)
                  </button>
                </div>
              </div>
            </div>

            <div class="col-span-12 lg:col-span-8">
              <h6 class="font-bold text-base mb-3">
                รายชื่อผู้มาติดต่อที่กำลังใช้งาน ({{ visitorItems.length }})
              </h6>
              <div
                tabindex="0"
                role="region"
                aria-label="ตารางรายชื่อผู้มาติดต่อ Visitor"
                class="sv-table-wrapper"
              >
                <table class="table whitespace-nowrap">
                  <thead>
                    <tr class="border-b border-defaultborder text-xs">
                      <th class="text-start p-3">ชื่อผู้มาติดต่อ</th>
                      <th class="text-start p-3">หน่วยงาน</th>
                      <th class="text-start p-3">วัตถุประสงค์</th>
                      <th class="text-start p-3">หมดอายุอัตโนมัติ</th>
                      <th class="text-start p-3">ใบหน้า 512-d</th>
                      <th class="text-end p-3">จัดการ</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let v of visitorItems" class="border-b border-defaultborder text-xs">
                      <th class="text-start p-3">
                        <div class="font-semibold">{{ v.fullName }}</div>
                        <div class="text-[0.7rem] text-dpu-muted">{{ v.phoneNumber || '-' }}</div>
                      </th>
                      <td class="p-3">{{ v.organization || '-' }}</td>
                      <td class="p-3">{{ v.visitPurpose || '-' }}</td>
                      <td class="p-3">{{ v.expiresAt ? (v.expiresAt | date:'dd/MM/yyyy HH:mm') : '12 ชม.' }}</td>
                      <td class="p-3">
                        <span *ngIf="v.hasFaceEnrolled" class="badge sv-pill-visitor px-2 py-0.5 rounded">
                          พร้อมใช้งาน
                        </span>
                        <label
                          *ngIf="!v.hasFaceEnrolled"
                          class="badge bg-amber-100 text-amber-800 px-2 py-0.5 rounded cursor-pointer"
                        >
                          + เพิ่มรูปหน้า
                          <input
                            type="file"
                            accept="image/*"
                            class="hidden"
                            (change)="enrollExistingIdentityFace(v.identityId, $event)"
                          />
                        </label>
                      </td>
                      <td class="p-3 text-end">
                        <button
                          type="button"
                          class="ti-btn ti-btn-sm ti-btn-danger"
                          (click)="deleteIdentity(v.identityId)"
                        >
                          ยกเลิกบัตร
                        </button>
                      </td>
                    </tr>
                    <tr *ngIf="visitorItems.length === 0">
                      <td colspan="6" class="text-center text-dpu-muted py-6">
                        ยังไม่มีผู้มาติดต่อที่ลงทะเบียนในขณะนี้
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- ================================================================
             TAB 5: SMART EVENTS & SEMINAR CHECK-IN
             ================================================================ -->
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'events'">
          <div class="grid grid-cols-12 gap-6">
            <!-- Create Event Form -->
            <div class="col-span-12 lg:col-span-4 p-5 rounded-xl border border-defaultborder bg-slate-50/60 space-y-5">
              <div>
                <h6 class="font-bold text-base mb-1">สร้างแคมเปญงานอีเวนต์ / งานสัมมนา</h6>
                <p class="text-xs text-dpu-muted mb-3">
                  ใช้ใบหน้าเดินเข้างานแบบไม่ต้องค้นหาบัตร พร้อมแสดงข้อความต้อนรับและเลขที่นั่งบนจอ Kiosk
                </p>

                <div class="grid grid-cols-12 gap-3">
                  <div class="col-span-12">
                    <label class="form-label text-xs font-semibold">ชื่องานอีเวนต์ / สัมมนา</label>
                    <input
                      class="form-control"
                      [(ngModel)]="eventForm.name"
                      placeholder="เช่น Townhall 2026 / AI Innovation Summit"
                    />
                  </div>
                  <div class="col-span-12 sm:col-span-6">
                    <label class="form-label text-xs font-semibold">ห้องประชุม / สถานที่จัดงาน</label>
                    <input class="form-control" [(ngModel)]="eventForm.locationName" placeholder="Grand Ballroom" />
                  </div>
                  <div class="col-span-12 sm:col-span-6">
                    <label class="form-label text-xs font-semibold">จำนวนที่นั่งรองรับ</label>
                    <input type="number" class="form-control" [(ngModel)]="eventForm.capacity" />
                  </div>
                  <div class="col-span-12">
                    <label class="form-label text-xs font-semibold">ข้อความต้อนรับบนจอ Kiosk</label>
                    <input
                      class="form-control"
                      [(ngModel)]="eventForm.welcomeMessage"
                      placeholder="ยินดีต้อนรับสู่งานสัมมนาประจำปี"
                    />
                  </div>
                  <div class="col-span-12">
                    <button
                      type="button"
                      class="ti-btn ti-btn-primary-full w-full font-semibold"
                      (click)="createEventCampaign()"
                    >
                      + เปิดแคมเปญงานอีเวนต์ใหม่
                    </button>
                  </div>
                </div>
              </div>

              <!-- Enroll Event Attendee -->
              <div class="pt-4 border-t border-defaultborder">
                <h6 class="font-bold text-sm mb-2">ลงทะเบียนผู้เข้าร่วมงาน + กำหนดหมายเลขที่นั่ง</h6>
                <div class="grid grid-cols-12 gap-3">
                  <div class="col-span-12">
                    <label class="form-label text-xs font-semibold">เลือกงานอีเวนต์</label>
                    <select class="form-control" [(ngModel)]="attendeeForm.eventId">
                      <option value="">-- เลือกงานอีเวนต์ --</option>
                      <option *ngFor="let ev of events" [value]="ev.eventId">{{ ev.name }}</option>
                    </select>
                  </div>
                  <div class="col-span-12 sm:col-span-7">
                    <label class="form-label text-xs font-semibold">ชื่อผู้เข้าร่วมงาน</label>
                    <input class="form-control" [(ngModel)]="attendeeForm.fullName" placeholder="ชื่อ - นามสกุล" />
                  </div>
                  <div class="col-span-12 sm:col-span-5">
                    <label class="form-label text-xs font-semibold">โต๊ะ / ที่นั่ง (Seat)</label>
                    <input class="form-control" [(ngModel)]="attendeeForm.seatNumber" placeholder="เช่น VIP-A01" />
                  </div>
                  <div class="col-span-12">
                    <label class="form-label text-xs font-semibold">รูปถ่ายใบหน้าผู้ร่วมงาน</label>
                    <input
                      type="file"
                      accept="image/*"
                      class="form-control"
                      (change)="onIdentityPhotoSelected($event)"
                    />
                  </div>
                  <div class="col-span-12">
                    <button
                      type="button"
                      class="ti-btn ti-btn-secondary-full w-full font-semibold"
                      (click)="createIdentityRecord(attendeeForm)"
                    >
                      + ลงทะเบียนผู้เข้าร่วมงานอีเวนต์
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Event Campaigns & Attendees List -->
            <div class="col-span-12 lg:col-span-8 space-y-5">
              <div>
                <h6 class="font-bold text-base mb-3">แคมเปญงานอีเวนต์ทั้งหมด ({{ events.length }})</h6>
                <div
                  tabindex="0"
                  role="region"
                  aria-label="ตารางแคมเปญงานอีเวนต์"
                  class="sv-table-wrapper"
                >
                  <table class="table whitespace-nowrap">
                    <thead>
                      <tr class="border-b border-defaultborder text-xs">
                        <th class="text-start p-3">ชื่องานอีเวนต์</th>
                        <th class="text-start p-3">สถานที่</th>
                        <th class="text-start p-3">ลงทะเบียนแล้ว</th>
                        <th class="text-start p-3">สแกนเข้างานแล้ว</th>
                        <th class="text-end p-3">จัดการ</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let ev of events" class="border-b border-defaultborder text-xs">
                        <th class="text-start p-3">
                          <div class="font-semibold">{{ ev.name }}</div>
                          <div class="text-[0.7rem] text-dpu-muted">{{ ev.welcomeMessage }}</div>
                        </th>
                        <td class="p-3">{{ ev.locationName || '-' }}</td>
                        <td class="p-3">
                          <span class="badge sv-pill-event px-2 py-0.5 rounded">
                            {{ ev.attendeeCount }} / {{ ev.capacity }} คน
                          </span>
                        </td>
                        <td class="p-3 font-bold text-emerald-700">{{ ev.checkedInCount }} คน</td>
                        <td class="p-3 text-end">
                          <button
                            type="button"
                            class="ti-btn ti-btn-sm ti-btn-danger"
                            (click)="deleteEvent(ev.eventId)"
                          >
                            ปิดงาน
                          </button>
                        </td>
                      </tr>
                      <tr *ngIf="events.length === 0">
                        <td colspan="5" class="text-center text-dpu-muted py-5">
                          ยังไม่มีแคมเปญงานอีเวนต์
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h6 class="font-bold text-base mb-3">
                  รายชื่อผู้ลงทะเบียนเข้างานอีเวนต์ ({{ eventAttendeeItems.length }})
                </h6>
                <div
                  tabindex="0"
                  role="region"
                  aria-label="ตารางรายชื่อผู้เข้าร่วมงานอีเวนต์"
                  class="sv-table-wrapper"
                >
                  <table class="table whitespace-nowrap">
                    <thead>
                      <tr class="border-b border-defaultborder text-xs">
                        <th class="text-start p-3">ชื่อผู้ร่วมงาน</th>
                        <th class="text-start p-3">หมายเลขที่นั่ง / โต๊ะ</th>
                        <th class="text-start p-3">ใบหน้า 512-d</th>
                        <th class="text-end p-3">จัดการ</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let att of eventAttendeeItems" class="border-b border-defaultborder text-xs">
                        <th class="text-start p-3">{{ att.fullName }}</th>
                        <td class="p-3">
                          <span class="badge bg-amber-100 text-amber-900 font-semibold px-2.5 py-0.5 rounded">
                            {{ att.seatNumber || 'General' }}
                          </span>
                        </td>
                        <td class="p-3">
                          <span *ngIf="att.hasFaceEnrolled" class="text-emerald-700 font-semibold">พร้อมสแกนเข้างาน</span>
                          <span *ngIf="!att.hasFaceEnrolled" class="text-amber-700">รออัปโหลดรูปหน้า</span>
                        </td>
                        <td class="p-3 text-end">
                          <button
                            type="button"
                            class="ti-btn ti-btn-sm ti-btn-danger"
                            (click)="deleteIdentity(att.identityId)"
                          >
                            ลบ
                          </button>
                        </td>
                      </tr>
                      <tr *ngIf="eventAttendeeItems.length === 0">
                        <td colspan="4" class="text-center text-dpu-muted py-5">
                          ยังไม่มีผู้ลงทะเบียนงานอีเวนต์
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ================================================================
             TAB 6: EMERGENCY MUSTER ROLL & EDGE AI FLEET SYNC
             ================================================================ -->
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'muster'">
          <div class="grid grid-cols-12 gap-6">
            <!-- Edge AI Sync Card -->
            <div class="col-span-12 lg:col-span-4 p-5 rounded-xl border border-defaultborder bg-slate-50/60 space-y-4">
              <div>
                <h6 class="font-bold text-base mb-1">
                  <i class="ri-cpu-line text-teal-700 me-1"></i>
                  สถานะซิงค์ฐานข้อมูลใบหน้า Edge AI (Offline-First Sync)
                </h6>
                <p class="text-xs text-dpu-muted mb-0">
                  ข้อมูล Manifest สำหรับเครื่องสแกนหน้างาน (Edge Box / Kiosk) เพื่อให้ทำงานได้ต่อเนื่องแม้เน็ตล่ม
                </p>
              </div>

              <div *ngIf="edgeManifest" class="space-y-2 text-xs bg-white p-4 rounded-lg border border-defaultborder">
                <div class="flex justify-between">
                  <span class="text-dpu-muted">รุ่น Manifest:</span>
                  <span class="font-mono font-semibold">{{ edgeManifest.manifestVersion }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-dpu-muted">โมเดล Biometric:</span>
                  <span class="font-semibold">{{ edgeManifest.embeddingModel }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-dpu-muted">ใบหน้าพนักงาน (Active):</span>
                  <span class="font-bold text-teal-700">{{ edgeManifest.employeeVectorsCount }} vectors</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-dpu-muted">ใบหน้า Watchlist/Visitor/Event:</span>
                  <span class="font-bold text-purple-700">{{ edgeManifest.sentinelVectorsCount }} vectors</span>
                </div>
                <div class="flex justify-between pt-2 border-t border-defaultborder">
                  <span class="font-semibold">รวม Vector พร้อมซิงค์ทั้งหมด:</span>
                  <span class="font-bold text-base text-slate-900">{{ edgeManifest.totalActiveVectors }}</span>
                </div>
              </div>

              <button
                type="button"
                class="ti-btn ti-btn-primary-full w-full font-semibold"
                (click)="loadEdgeManifest()"
              >
                <i class="ri-refresh-line me-1"></i> อัปเดต Edge Manifest ล่าสุด
              </button>
            </div>

            <!-- Live Building Occupancy / Emergency Muster Roll -->
            <div class="col-span-12 lg:col-span-8">
              <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div>
                  <h6 class="font-bold text-base mb-0">
                    รายชื่อบุคคลที่อยู่ในพื้นที่อาคารวันนี้ (Live Occupancy &amp; Emergency Muster Roll)
                  </h6>
                  <p class="text-xs text-dpu-muted mb-0">
                    ใช้ตรวจสอบยอดพนักงานและผู้มาติดต่อในกรณีเกิดเหตุฉุกเฉินหรืออพยพหนีไฟ
                  </p>
                </div>
                <span class="badge bg-emerald-100 text-emerald-800 px-3 py-1 text-xs font-bold">
                  รวมในพื้นที่วันนี้ {{ (overview?.musterRoll || []).length }} คน
                </span>
              </div>

              <div
                tabindex="0"
                role="region"
                aria-label="ตารางรายชื่อบุคคลในอาคารวันนี้ Emergency Muster Roll"
                class="sv-table-wrapper"
              >
                <table class="table whitespace-nowrap">
                  <thead>
                    <tr class="border-b border-defaultborder text-xs">
                      <th class="text-start p-3">ชื่อ - นามสกุล</th>
                      <th class="text-start p-3">ประเภทบุคคล</th>
                      <th class="text-start p-3">รหัสอ้างอิง</th>
                      <th class="text-start p-3">จุดสแกนล่าสุด</th>
                      <th class="text-end p-3">เวลาที่พบล่าสุด</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      *ngFor="let person of overview?.musterRoll || []"
                      class="border-b border-defaultborder text-xs"
                    >
                      <th class="text-start p-3 font-semibold">{{ person.fullName }}</th>
                      <td class="p-3">
                        <span
                          class="badge px-2 py-0.5 rounded"
                          [ngClass]="
                            person.category === 'EMPLOYEE'
                              ? 'bg-teal-100 text-teal-800'
                              : 'sv-pill-visitor'
                          "
                        >
                          {{ person.category }}
                        </span>
                      </td>
                      <td class="p-3">{{ person.badgeCode }}</td>
                      <td class="p-3">{{ person.zoneOrLocation }}</td>
                      <td class="p-3 text-end">{{ person.lastSeenAt | date:'dd/MM HH:mm:ss' }}</td>
                    </tr>
                    <tr *ngIf="!(overview?.musterRoll?.length)">
                      <td colspan="5" class="text-center text-dpu-muted py-6">
                        ยังไม่มีประวัติการสแกนเข้าอาคารในวันนี้
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class SentinelCenterComponent implements OnInit {
  companyId = '';
  activeTab: SentinelTab = 'command';
  /** True when opened via `/company/{module}/:section` thin routes. */
  moduleScoped = false;
  moduleWorkspaceLabel = '';
  isLoading = false;
  isScanning = false;
  toastMessage = '';

  overview: any = null;
  identities: any[] = [];
  zones: any[] = [];
  events: any[] = [];
  incidents: any[] = [];
  edgeManifest: any = null;

  incidentFilterSeverity = '';
  selectedIdentityPhoto: File | null = null;
  scanSelectedFile: File | null = null;
  lastScanResult: any = null;

  scanForm = {
    stationMode: 'ACCESS_CONTROL',
    zoneId: '',
    eventId: '',
    totpOrPin: '',
  };

  watchlistForm = {
    identityType: 'BLACKLIST',
    severity: 'CRITICAL',
    fullName: '',
    documentRef: '',
    organization: '',
    alertNote: '',
  };

  visitorForm = {
    identityType: 'VISITOR',
    severity: 'LOW',
    fullName: '',
    organization: '',
    phoneNumber: '',
    visitPurpose: '',
    expiresAt: '',
  };

  attendeeForm = {
    identityType: 'EVENT_ATTENDEE',
    severity: 'LOW',
    eventId: '',
    fullName: '',
    seatNumber: '',
  };

  zoneForm = {
    name: '',
    code: 'GATE-01',
    stationMode: 'ACCESS_CONTROL',
    scheduleStart: '07:00',
    scheduleEnd: '20:00',
    allowEmployee: true,
    allowVip: true,
    allowVisitor: true,
    require2FA: false,
    relayWebhookUrl: '',
  };

  eventForm = {
    name: '',
    locationName: 'Main Auditorium',
    capacity: 200,
    welcomeMessage: '',
  };

  constructor(
    private http: HttpClient,
    private tokenService: TokenService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    const company = this.tokenService.getSelectCompany();
    this.companyId = company?.companyId || '';

    const workspace = this.route.snapshot.data['moduleWorkspace'] as string | undefined;
    const section = this.route.snapshot.paramMap.get('section');
    const mapped = tabFromModuleSection(workspace, section);
    if (mapped) {
      this.moduleScoped = true;
      this.activeTab = mapped;
      this.moduleWorkspaceLabel = this.labelForWorkspace(workspace!, section);
      if (mapped === 'muster' && !this.edgeManifest) {
        // defer until companyId reload; loadEdgeManifest runs via reloadAll
      }
    } else {
      // Legacy `/company/sentinel-center?tab=` → dedicated module routes.
      const tab = this.route.snapshot.queryParamMap.get('tab');
      if (tab && LEGACY_TAB_REDIRECTS[tab]) {
        this.router.navigateByUrl(LEGACY_TAB_REDIRECTS[tab], { replaceUrl: true });
        return;
      }
    }

    if (this.companyId) {
      this.reloadAll();
    }
  }

  private labelForWorkspace(workspace: string, section: string | null): string {
    const sectionLabel = section ? ` / ${section}` : '';
    switch (workspace) {
      case 'ACCESS_CONTROL':
        return `Access Control${sectionLabel}`;
      case 'WATCHLIST':
        return `Watchlist${sectionLabel}`;
      case 'VISITOR':
        return `Visitor${sectionLabel}`;
      case 'EVENTS':
        return `Events${sectionLabel}`;
      default:
        return workspace;
    }
  }

  get watchlistItems(): any[] {
    return this.identities.filter((i) =>
      ['BLACKLIST', 'POI', 'VIP'].includes(i.identityType)
    );
  }

  get visitorItems(): any[] {
    return this.identities.filter((i) => i.identityType === 'VISITOR');
  }

  get eventAttendeeItems(): any[] {
    return this.identities.filter((i) => i.identityType === 'EVENT_ATTENDEE');
  }

  setTab(tab: SentinelTab): void {
    if (this.moduleScoped) {
      return;
    }
    this.activeTab = tab;
    if (tab === 'muster' && !this.edgeManifest) {
      this.loadEdgeManifest();
    }
  }

  private showToast(msg: string): void {
    this.toastMessage = msg;
    setTimeout(() => {
      if (this.toastMessage === msg) {
        this.toastMessage = '';
      }
    }, 4000);
  }

  reloadAll(): void {
    if (!this.companyId) return;
    this.isLoading = true;
    this.loadOverview();
    this.loadIdentities();
    this.loadZones();
    this.loadEvents();
    this.loadIncidents();
    this.loadEdgeManifest();
  }

  loadOverview(): void {
    this.http.get(`/sentinel/company/${this.companyId}/overview`).subscribe({
      next: (res) => {
        this.overview = res;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      },
    });
  }

  loadIdentities(): void {
    this.http.get<any[]>(`/sentinel/company/${this.companyId}/identities`).subscribe({
      next: (rows) => {
        this.identities = rows || [];
      },
    });
  }

  loadZones(): void {
    this.http.get<any[]>(`/sentinel/company/${this.companyId}/zones`).subscribe({
      next: (rows) => {
        this.zones = rows || [];
      },
    });
  }

  loadEvents(): void {
    this.http.get<any[]>(`/sentinel/company/${this.companyId}/events`).subscribe({
      next: (rows) => {
        this.events = rows || [];
        if (this.events.length > 0 && !this.attendeeForm.eventId) {
          this.attendeeForm.eventId = this.events[0].eventId;
        }
      },
    });
  }

  loadIncidents(): void {
    const q = this.incidentFilterSeverity ? `?severity=${this.incidentFilterSeverity}` : '';
    this.http.get<any[]>(`/sentinel/company/${this.companyId}/incidents${q}`).subscribe({
      next: (rows) => {
        this.incidents = rows || [];
      },
    });
  }

  loadEdgeManifest(): void {
    this.http.get(`/sentinel/company/${this.companyId}/edge-sync`).subscribe({
      next: (res) => {
        this.edgeManifest = res;
      },
    });
  }

  onIdentityPhotoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedIdentityPhoto = input.files && input.files.length > 0 ? input.files[0] : null;
  }

  onScanFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.scanSelectedFile = input.files && input.files.length > 0 ? input.files[0] : null;
  }

  createIdentityRecord(formObj: any): void {
    if (!formObj.fullName || !String(formObj.fullName).trim()) {
      this.showToast('กรุณาระบุชื่อ-นามสกุล');
      return;
    }
    this.http.post<any>(`/sentinel/company/${this.companyId}/identities`, formObj).subscribe({
      next: (created) => {
        const photo = this.selectedIdentityPhoto;
        this.selectedIdentityPhoto = null;
        formObj.fullName = '';
        if (photo && created?.identityId) {
          this.uploadIdentityFace(created.identityId, photo);
        } else {
          this.showToast('บันทึกรายชื่อสำเร็จ');
          this.reloadAll();
        }
      },
    });
  }

  enrollExistingIdentityFace(identityId: string, event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files && input.files.length > 0 ? input.files[0] : null;
    if (!file) return;
    this.uploadIdentityFace(identityId, file);
  }

  private uploadIdentityFace(identityId: string, file: File): void {
    const fd = new FormData();
    fd.append('file', file);
    this.http
      .post(`/sentinel/company/${this.companyId}/identities/${identityId}/enroll-face`, fd)
      .subscribe({
        next: () => {
          this.showToast('ลงทะเบียนใบหน้า 512-d สำเร็จ');
          this.reloadAll();
        },
        error: (err) => {
          this.showToast(err?.error?.detail || 'ไม่พบใบหน้าในภาพที่อัปโหลด');
          this.reloadAll();
        },
      });
  }

  deleteIdentity(identityId: string): void {
    this.http.delete(`/sentinel/company/${this.companyId}/identities/${identityId}`).subscribe({
      next: () => {
        this.showToast('ลบรายการเรียบร้อยแล้ว');
        this.reloadAll();
      },
    });
  }

  createAccessZone(): void {
    if (!this.zoneForm.name.trim()) {
      this.showToast('กรุณาระบุชื่อโซนหรือประตู');
      return;
    }
    const allowedIdentityTypes: string[] = [];
    if (this.zoneForm.allowEmployee) allowedIdentityTypes.push('EMPLOYEE');
    if (this.zoneForm.allowVip) allowedIdentityTypes.push('VIP');
    if (this.zoneForm.allowVisitor) allowedIdentityTypes.push('VISITOR');

    this.http
      .post(`/sentinel/company/${this.companyId}/zones`, {
        ...this.zoneForm,
        allowedIdentityTypes,
      })
      .subscribe({
        next: () => {
          this.zoneForm.name = '';
          this.showToast('สร้างโซนประตู Access Control สำเร็จ');
          this.reloadAll();
        },
      });
  }

  remoteUnlockZone(zoneId: string): void {
    this.http
      .post(`/sentinel/company/${this.companyId}/zones/${zoneId}/trigger`, {
        reason: 'Admin Console Remote Unlock',
      })
      .subscribe({
        next: () => {
          this.showToast('ส่งคำสั่งปลดล็อกประตูเรียบร้อยแล้ว');
          this.loadIncidents();
          this.loadOverview();
        },
      });
  }

  deleteZone(zoneId: string): void {
    this.http.delete(`/sentinel/company/${this.companyId}/zones/${zoneId}`).subscribe({
      next: () => {
        this.showToast('ลบโซนประตูเรียบร้อยแล้ว');
        this.reloadAll();
      },
    });
  }

  createEventCampaign(): void {
    if (!this.eventForm.name.trim()) {
      this.showToast('กรุณาระบุชื่องานอีเวนต์');
      return;
    }
    this.http.post(`/sentinel/company/${this.companyId}/events`, this.eventForm).subscribe({
      next: () => {
        this.eventForm.name = '';
        this.showToast('สร้างแคมเปญงานอีเวนต์สำเร็จ');
        this.reloadAll();
      },
    });
  }

  deleteEvent(eventId: string): void {
    this.http.delete(`/sentinel/company/${this.companyId}/events/${eventId}`).subscribe({
      next: () => {
        this.showToast('ปิดแคมเปญงานอีเวนต์แล้ว');
        this.reloadAll();
      },
    });
  }

  runUnifiedScan(): void {
    if (!this.scanSelectedFile) return;
    this.isScanning = true;
    const fd = new FormData();
    fd.append('file', this.scanSelectedFile);
    fd.append('stationMode', this.scanForm.stationMode);
    if (this.scanForm.zoneId) fd.append('zoneId', this.scanForm.zoneId);
    if (this.scanForm.eventId) fd.append('eventId', this.scanForm.eventId);
    if (this.scanForm.totpOrPin) fd.append('totpOrPin', this.scanForm.totpOrPin);

    this.http.post(`/sentinel/company/${this.companyId}/scan`, fd).subscribe({
      next: (res) => {
        this.isScanning = false;
        this.lastScanResult = res;
        this.loadIncidents();
        this.loadOverview();
        this.loadEvents();
      },
      error: (err) => {
        this.isScanning = false;
        this.lastScanResult = {
          accessGranted: false,
          decision: 'SCAN_ERROR',
          message: err?.error?.detail || 'เกิดข้อผิดพลาดในการประมวลผลใบหน้า',
        };
      },
    });
  }

  acknowledgeIncident(incidentId: string): void {
    this.http
      .post(`/sentinel/company/${this.companyId}/incidents/${incidentId}/acknowledge`, {})
      .subscribe({
        next: () => {
          this.showToast('รับทราบเหตุการณ์แล้ว');
          this.loadIncidents();
          this.loadOverview();
        },
      });
  }
}
