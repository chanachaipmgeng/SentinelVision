import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';
import { PermissionService } from '../../../shared/services/permission.service';

interface FleetSummary {
  healthScore: number;
  kiosksTotal: number;
  kiosksOnline: number;
  kiosksStale: number;
  kiosksOffline: number;
  camerasTotal: number;
  camerasConnected: number;
  camerasOffline: number;
  zonesTotal: number;
  zonesActive: number;
  unreadAlerts: number;
  aiQueuePending: number;
  aiQueueActive: number;
}

interface KioskHealthItem {
  deviceId: string;
  name: string;
  locationLabel?: string | null;
  stationMode?: string | null;
  appVersion?: string | null;
  fingerprint?: string | null;
  healthStatus: 'ONLINE' | 'STALE' | 'OFFLINE';
  lastHeartbeatAt?: string | null;
  lastSeenAgoSeconds?: number | null;
  isPaired: boolean;
}

interface CameraHealthItem {
  cameraId: string;
  name: string;
  protocol: string;
  recordMode: string;
  status: string;
  isActive: boolean;
  latencyMs?: number | null;
  lastPingAt?: string | null;
}

interface FleetHealthResponse {
  generatedAt: string;
  summary: FleetSummary;
  kiosks: {
    items: KioskHealthItem[];
    byMode: Record<string, number>;
    byVersion: Record<string, number>;
  };
  cameras: {
    items: CameraHealthItem[];
  };
}

@Component({
  selector: 'app-fleet-health',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, SharedModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-page-header [title]="'Fleet & Edge Health'" [activeTitle]="'System Health'" [title1]="'SentinelVision'"></app-page-header>

    <div class="dpu-list-page min-w-0 max-w-full space-y-4">
      <!-- Operational Topbar (Reusable Wrapper) -->
      <app-command-topbar
        icon="ri-pulse-line"
        accent="cyan"
        badgeText="LIVE FLEET TELEMETRY"
        title="ศูนย์ตรวจวัดสุขภาพอุปกรณ์และเซ็นเซอร์ Edge"
        [lastUpdated]="lastUpdated"
      >
        <ng-container actions>
          <button
            type="button"
            (click)="refresh()"
            [disabled]="loading"
            class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-1.5"
          >
            <i class="ri-refresh-line" [class.animate-spin]="loading"></i>
            <span>รีเฟรชข้อมูล</span>
          </button>
          <a routerLink="/company/devices" class="ti-btn ti-btn-primary-full modern-btn text-xs px-3 py-1.5 rounded-lg">
            <i class="ri-device-line me-1"></i>
            <span>จัดการ Kiosk</span>
          </a>
        </ng-container>
      </app-command-topbar>

      <!-- 6-Segment Metric Ribbon Standard (Reusable Wrapper) -->
      <app-metric-ribbon [columns]="6">
        <!-- Metric 1: Overall Health Score -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">ดัชนีความพร้อมรวม</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold" [ngClass]="summary.healthScore >= 90 ? 'text-emerald-400' : (summary.healthScore >= 70 ? 'text-amber-400' : 'text-rose-400')">
              {{ summary.healthScore }}%
            </span>
          </div>
          <span
            class="text-[11px] flex items-center gap-1 font-medium"
            [ngClass]="summary.healthScore >= 90 ? 'text-emerald-400' : (summary.healthScore >= 70 ? 'text-amber-400' : 'text-rose-400')"
          >
            <i [class]="summary.healthScore >= 90 ? 'ri-shield-check-line' : (summary.healthScore >= 70 ? 'ri-error-warning-line' : 'ri-close-circle-line')"></i>
            {{ summary.healthScore >= 90 ? 'เสถียรภาพสูง' : (summary.healthScore >= 70 ? 'เฝ้าระวัง' : 'วิกฤต / ออฟไลน์') }}
          </span>
        </div>

        <!-- Metric 2: Kiosks Online -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">Kiosk ออนไลน์</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-cyan-400">
              {{ summary.kiosksOnline }} <span class="text-sm font-normal text-slate-400">/ {{ summary.kiosksTotal }}</span>
            </span>
          </div>
          <span class="text-[11px] text-cyan-300 flex items-center gap-1">
            <i class="ri-macbook-line"></i> ประจำจุดเข้า-ออก
          </span>
        </div>

        <!-- Metric 3: CCTV Connected -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">กล้อง CCTV</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-violet-400">
              {{ summary.camerasConnected }} <span class="text-sm font-normal text-slate-400">/ {{ summary.camerasTotal }}</span>
            </span>
          </div>
          <span class="text-[11px] text-violet-300 flex items-center gap-1">
            <i class="ri-vidicon-line"></i> สตรีมเรียลไทม์
          </span>
        </div>

        <!-- Metric 4: Active Zones -->
        <div class="p-4 border-b lg:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">โซนควบคุมสิทธิ์</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-sky-400">
              {{ summary.zonesActive }} <span class="text-sm font-normal text-slate-400">โซน</span>
            </span>
          </div>
          <span class="text-[11px] text-sky-300 flex items-center gap-1">
            <i class="ri-door-lock-line"></i> Anti-Passback ป้องกัน
          </span>
        </div>

        <!-- Metric 5: AI Engine Status (Cluster Queue for System Admin; Ready status for Company Admin) -->
        <div class="p-4 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">{{ isSystemAdmin ? 'AI GPU Queue' : 'สถานะระบบ AI' }}</span>
          <div class="my-1.5">
            <span *ngIf="isSystemAdmin" class="text-2xl font-mono font-bold text-emerald-400">
              {{ summary.aiQueuePending }} <span class="text-sm font-normal text-slate-400">คิว</span>
            </span>
            <span *ngIf="!isSystemAdmin" class="text-xl font-mono font-bold text-emerald-400">
              พร้อมใช้งาน
            </span>
          </div>
          <span class="text-[11px] text-emerald-300 flex items-center gap-1">
            <i class="ri-cpu-line"></i>
            <ng-container *ngIf="isSystemAdmin">
              <a routerLink="/admin/infrastructure" class="hover:underline">ดูคลัสเตอร์ GPU</a>
            </ng-container>
            <ng-container *ngIf="!isSystemAdmin">ประมวลผลชีวมิติปกติ</ng-container>
          </span>
        </div>

        <!-- Metric 6: Unread Alerts -->
        <div class="p-4 flex flex-col justify-between">
          <span class="text-xs text-slate-400">เหตุการณ์รอตรวจ</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold" [ngClass]="summary.unreadAlerts > 0 ? 'text-amber-400' : 'text-slate-300'">
              {{ summary.unreadAlerts }} <span class="text-sm font-normal text-slate-400">รายการ</span>
            </span>
          </div>
          <span class="text-[11px] text-slate-400 flex items-center gap-1">
            <i class="ri-notification-3-line"></i> 24 ชั่วโมงล่าสุด
          </span>
        </div>
      </app-metric-ribbon>

      <!-- Navigation Tabs -->
      <div class="flex items-center gap-2 border-b border-white/10 pb-2">
        <button
          type="button"
          (click)="activeTab = 'kiosks'"
          [class.border-cyan-400]="activeTab === 'kiosks'"
          [class.text-cyan-400]="activeTab === 'kiosks'"
          class="px-4 py-2 text-xs font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition flex items-center gap-1.5"
        >
          <i class="ri-macbook-line"></i>
          Kiosk Terminals ({{ kiosks.length }})
        </button>
        <button
          type="button"
          (click)="activeTab = 'cameras'"
          [class.border-cyan-400]="activeTab === 'cameras'"
          [class.text-cyan-400]="activeTab === 'cameras'"
          class="px-4 py-2 text-xs font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition flex items-center gap-1.5"
        >
          <i class="ri-camera-lens-line"></i>
          CCTV Sensors ({{ cameras.length }})
        </button>
      </div>

      <!-- Tab Content: Kiosks -->
      <div *ngIf="activeTab === 'kiosks'" class="rounded-2xl border border-white/10 bg-[#070d14] overflow-hidden shadow-xl">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="border-b border-white/10 bg-slate-900/50 text-slate-400 uppercase text-[10px] font-mono tracking-wider">
                <th class="py-3 px-4">ชื่ออุปกรณ์ Kiosk</th>
                <th class="py-3 px-4">โหมดการทำงาน (Station Mode)</th>
                <th class="py-3 px-4">เวอร์ชัน & รหัสฮาร์ดแวร์</th>
                <th class="py-3 px-4">สถานะการเชื่อมต่อ</th>
                <th class="py-3 px-4">ส่งสัญญาณล่าสุด (Heartbeat)</th>
                <th class="py-3 px-4 text-right">การจัดการ</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              <tr *ngFor="let k of kiosks" class="hover:bg-white/[0.02] transition">
                <td class="py-3.5 px-4">
                  <div class="font-bold text-slate-100">{{ k.name }}</div>
                  <div *ngIf="k.locationLabel" class="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                    <i class="ri-map-pin-line text-cyan-400"></i>
                    {{ k.locationLabel }}
                  </div>
                </td>
                <td class="py-3.5 px-4">
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold" [ngClass]="getStationModeClass(k.stationMode)">
                    {{ k.stationMode || 'UNCONFIGURED' }}
                  </span>
                </td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-slate-300">
                  <div>v{{ k.appVersion || '1.0.0' }}</div>
                  <div *ngIf="k.fingerprint" class="text-[10px] text-slate-400 truncate max-w-[140px]">{{ k.fingerprint }}</div>
                </td>
                <td class="py-3.5 px-4">
                  <span *ngIf="k.healthStatus === 'ONLINE'" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[11px] font-medium">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> ออนไลน์
                  </span>
                  <span *ngIf="k.healthStatus === 'STALE'" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[11px] font-medium">
                    <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> ขาดการส่งสัญญาณชั่วคราว
                  </span>
                  <span *ngIf="k.healthStatus === 'OFFLINE'" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30 text-[11px] font-medium">
                    <span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span> ออฟไลน์
                  </span>
                </td>
                <td class="py-3.5 px-4 text-slate-300">
                  <div *ngIf="k.lastHeartbeatAt">
                    {{ k.lastHeartbeatAt | date: 'dd/MM/yyyy HH:mm:ss' }}
                    <span class="text-[10px] text-slate-400 block" *ngIf="k.lastSeenAgoSeconds !== null">
                      ({{ formatAgo(k.lastSeenAgoSeconds) }})
                    </span>
                  </div>
                  <span *ngIf="!k.lastHeartbeatAt" class="text-slate-400 italic">ไม่เคยส่งสัญญาณ</span>
                </td>
                <td class="py-3.5 px-4 text-right">
                  <a routerLink="/company/devices" class="ti-btn ti-btn-light text-xs px-2.5 py-1 rounded-lg border border-white/10 hover:text-cyan-400">
                    <i class="ri-settings-4-line"></i>
                  </a>
                </td>
              </tr>
              <tr *ngIf="!kiosks.length">
                <td colspan="6" class="py-8 text-center text-slate-400">ยังไม่มีอุปกรณ์ Kiosk ที่ลงทะเบียนในระบบ</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tab Content: Cameras -->
      <div *ngIf="activeTab === 'cameras'" class="rounded-2xl border border-white/10 bg-[#070d14] overflow-hidden shadow-xl">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="border-b border-white/10 bg-slate-900/50 text-slate-400 uppercase text-[10px] font-mono tracking-wider">
                <th class="py-3 px-4">ชื่อกล้อง CCTV</th>
                <th class="py-3 px-4">โพรโทคอล & โหมดบันทึก</th>
                <th class="py-3 px-4">สถานะสตรีมมิ่ง</th>
                <th class="py-3 px-4">ค่าความหน่วง (Latency)</th>
                <th class="py-3 px-4 text-right">การจัดการ</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              <tr *ngFor="let c of cameras" class="hover:bg-white/[0.02] transition">
                <td class="py-3.5 px-4 font-bold text-slate-100">{{ c.name }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-300">
                  <span class="badge bg-violet-500/20 text-violet-300 border border-violet-500/30 text-[10px] px-2 py-0.5 rounded">
                    {{ c.protocol | uppercase }}
                  </span>
                  <span class="text-[11px] text-slate-400 ms-2">บันทึก: {{ c.recordMode }}</span>
                </td>
                <td class="py-3.5 px-4">
                  <span *ngIf="c.isActive && (c.status === 'online' || c.status === 'active' || c.status === 'connected')" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[11px] font-medium">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> เชื่อมต่อแล้ว
                  </span>
                  <span *ngIf="!c.isActive || (c.status !== 'online' && c.status !== 'active' && c.status !== 'connected')" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30 text-[11px] font-medium">
                    <span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span> ขาดการเชื่อมต่อ
                  </span>
                </td>
                <td class="py-3.5 px-4 font-mono text-slate-300">
                  <ng-container *ngIf="c.isActive && (c.status === 'online' || c.status === 'active' || c.status === 'connected'); else offlineLatency">
                    {{ c.latencyMs ? c.latencyMs + ' ms' : 'ปกติ' }}
                  </ng-container>
                  <ng-template #offlineLatency>
                    <span class="text-slate-500">—</span>
                  </ng-template>
                </td>
                <td class="py-3.5 px-4 text-right">
                  <a routerLink="/company/cameras" class="ti-btn ti-btn-light text-xs px-2.5 py-1 rounded-lg border border-white/10 hover:text-cyan-400">
                    <i class="ri-settings-4-line"></i>
                  </a>
                </td>
              </tr>
              <tr *ngIf="!cameras.length">
                <td colspan="5" class="py-8 text-center text-slate-400">ยังไม่มีกล้อง CCTV ที่ลงทะเบียนในระบบ</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `,
})
export class FleetHealthComponent implements OnInit, OnDestroy {
  loading = false;
  activeTab: 'kiosks' | 'cameras' = 'kiosks';
  lastUpdated: Date | null = null;
  refreshTimer: ReturnType<typeof setInterval> | null = null;

  summary: FleetSummary = {
    healthScore: 100,
    kiosksTotal: 0,
    kiosksOnline: 0,
    kiosksStale: 0,
    kiosksOffline: 0,
    camerasTotal: 0,
    camerasConnected: 0,
    camerasOffline: 0,
    zonesTotal: 0,
    zonesActive: 0,
    unreadAlerts: 0,
    aiQueuePending: 0,
    aiQueueActive: 0,
  };

  kiosks: KioskHealthItem[] = [];
  cameras: CameraHealthItem[] = [];

  constructor(
    private http: HttpClient,
    private tokenService: TokenService,
    private permissions: PermissionService,
    private cdr: ChangeDetectorRef,
  ) {}

  get isSystemAdmin(): boolean {
    return this.permissions.isSystemAdmin();
  }

  ngOnInit(): void {
    this.refresh();
    // Auto-refresh every 30 seconds
    this.refreshTimer = setInterval(() => {
      this.refresh(false);
    }, 30000);
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  get companyId(): string {
    return this.tokenService.getSelectCompany()?.companyId || '';
  }

  refresh(showLoading = true): void {
    if (!this.companyId) return;
    if (showLoading) {
      this.loading = true;
      this.cdr.markForCheck();
    }
    this.http.get<FleetHealthResponse>(`/sentinel/company/${this.companyId}/fleet-health`).subscribe({
      next: (res) => {
        this.summary = res.summary || this.summary;
        this.kiosks = res.kiosks?.items || [];
        this.cameras = res.cameras?.items || [];
        this.lastUpdated = new Date();
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  formatAgo(sec: number | null | undefined): string {
    if (sec === null || sec === undefined) return '';
    if (sec < 60) return `${sec} วินาทีที่แล้ว`;
    if (sec < 3600) return `${Math.floor(sec / 60)} นาทีที่แล้ว`;
    return `${Math.floor(sec / 3600)} ชม. ที่แล้ว`;
  }

  getStationModeClass(mode?: string | null): string {
    switch (mode) {
      case 'ATTENDANCE':
        return 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40';
      case 'ACCESS_CONTROL':
        return 'bg-sky-500/20 text-sky-300 border border-sky-500/40';
      case 'WATCHLIST_MONITOR':
        return 'bg-rose-500/20 text-rose-300 border border-rose-500/40';
      case 'VISITOR_CHECKIN':
        return 'bg-violet-500/20 text-violet-300 border border-violet-500/40';
      case 'EVENT_CHECKIN':
        return 'bg-amber-500/20 text-amber-300 border border-amber-500/40';
      default:
        return 'bg-teal-500/20 text-teal-300 border border-teal-500/40';
    }
  }
}
