import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';

interface ReadyPayload {
  status?: string;
  queue?: {
    started?: boolean;
    workers?: number;
    pending?: number;
    active?: number;
    completed?: number;
    maxsize?: number;
    devices?: string[];
    pendingByKind?: Record<string, number>;
  };
  schema?: {
    status?: string;
    current?: string;
    head?: string;
  };
}

@Component({
  selector: 'app-platform-infrastructure',
  standalone: true,
  imports: [CommonModule, RouterLink, SharedModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-page-header
      [title]="'Platform Infrastructure'"
      [activeTitle]="'System Admin'"
      [title1]="'Infrastructure & GPU'"
    ></app-page-header>

    <div class="dpu-list-page min-w-0 max-w-full space-y-4">
      <app-command-topbar
        icon="ri-server-line"
        accent="cyan"
        badgeText="SYSTEM ADMIN CLUSTER TELEMETRY"
        title="ศูนย์ควบคุมโครงสร้างพื้นฐานแพลตฟอร์ม, GPU Workers & Multi-Region DR"
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
            <span>รีเฟรชคลัสเตอร์</span>
          </button>
          <a routerLink="/admin/manage-companys" class="ti-btn ti-btn-primary-full modern-btn text-xs px-3 py-1.5 rounded-lg">
            <i class="ri-building-line me-1"></i>
            <span>จัดการผู้เช่า / โควตา</span>
          </a>
        </ng-container>
      </app-command-topbar>

      <app-metric-ribbon [columns]="6">
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed sv-border-subtle flex flex-col justify-between">
          <span class="text-xs sv-text-muted">สถานะ API Cluster</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold" [ngClass]="ready?.status === 'ok' ? 'text-emerald-400' : 'text-rose-400'">
              {{ ready?.status === 'ok' ? 'HEALTHY' : 'DEGRADED' }}
            </span>
          </div>
          <span class="text-[11px] text-emerald-400 flex items-center gap-1">
            <i class="ri-checkbox-circle-line"></i> /health &amp; /ready OK
          </span>
        </div>

        <div class="p-4 border-b sm:border-b-0 border-r border-dashed sv-border-subtle flex flex-col justify-between">
          <span class="text-xs sv-text-muted">GPU Devices</span>
          <div class="my-1.5">
            <span class="text-xl font-mono font-bold text-cyan-400">
              {{ gpuDevicesLabel }}
            </span>
          </div>
          <span class="text-[11px] text-cyan-300 flex items-center gap-1">
            <i class="ri-cpu-line"></i> InsightFace buffalo_l
          </span>
        </div>

        <div class="p-4 border-b sm:border-b-0 border-r border-dashed sv-border-subtle flex flex-col justify-between">
          <span class="text-xs sv-text-muted">AI Workers</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-violet-400">
              {{ ready?.queue?.workers ?? 0 }}
            </span>
          </div>
          <span class="text-[11px] text-violet-300 flex items-center gap-1">
            <i class="ri-flashlight-line"></i> Active: {{ ready?.queue?.active ?? 0 }}
          </span>
        </div>

        <div class="p-4 border-b lg:border-b-0 border-r border-dashed sv-border-subtle flex flex-col justify-between">
          <span class="text-xs sv-text-muted">Global AI Queue</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-sky-400">
              {{ ready?.queue?.pending ?? 0 }} <span class="text-xs font-normal sv-text-muted">/ {{ ready?.queue?.maxsize ?? 64 }}</span>
            </span>
          </div>
          <span class="text-[11px] text-sky-300 flex items-center gap-1">
            <i class="ri-stack-line"></i> Completed: {{ ready?.queue?.completed ?? 0 }}
          </span>
        </div>

        <div class="p-4 border-r border-dashed sv-border-subtle flex flex-col justify-between">
          <span class="text-xs sv-text-muted">Database Schema</span>
          <div class="my-1.5">
            <span class="text-sm font-mono font-bold text-emerald-400 break-all">
              {{ ready?.schema?.current || '—' }}
            </span>
          </div>
          <span class="text-[11px] text-emerald-300 flex items-center gap-1">
            <i class="ri-database-2-line"></i> {{ ready?.schema?.status === 'ok' ? 'Alembic Synced' : 'Check Drift' }}
          </span>
        </div>

        <div class="p-4 flex flex-col justify-between">
          <span class="text-xs sv-text-muted">Multi-Region DR</span>
          <div class="my-1.5">
            <span class="text-lg font-mono font-bold text-teal-400">HMAC-SHA256</span>
          </div>
          <span class="text-[11px] sv-text-muted flex items-center gap-1">
            <i class="ri-global-line"></i> Platform-only scope
          </span>
        </div>
      </app-metric-ribbon>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Queue Breakdown -->
        <div class="sv-surface-panel sv-motion-enter sv-stagger-2 rounded-2xl p-5 shadow-lg space-y-3">
          <div class="flex items-center justify-between border-b sv-border-subtle pb-3">
            <h3 class="text-sm font-bold sv-text-primary mb-0 flex items-center gap-2">
              <i class="ri-bar-chart-grouped-line text-cyan-400"></i>
              <span>การกระจายงานคิวประมวลผล GPU (Pending by Kind)</span>
            </h3>
            <span class="text-[11px] font-mono sv-text-muted">Shared Cluster</span>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
            <div *ngFor="let item of queueKinds" class="p-3 rounded-xl border sv-border-subtle bg-white/[0.02]">
              <div class="sv-text-muted uppercase font-mono text-[10px]">{{ item.key }}</div>
              <div class="text-xl font-mono font-bold sv-text-primary mt-1">{{ item.value }}</div>
            </div>
          </div>
        </div>

        <!-- Platform Governance Shortcuts -->
        <div class="sv-surface-panel sv-motion-enter sv-stagger-3 rounded-2xl p-5 shadow-lg space-y-3">
          <div class="flex items-center justify-between border-b sv-border-subtle pb-3">
            <h3 class="text-sm font-bold sv-text-primary mb-0 flex items-center gap-2">
              <i class="ri-shield-keyhole-line text-emerald-400"></i>
              <span>ศูนย์ควบคุมระดับผู้ดูแลระบบ (System Admin Only)</span>
            </h3>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <a routerLink="/admin/manage-companys" class="p-3 rounded-xl border sv-border-subtle hover:border-cyan-400/50 transition flex items-center gap-3">
              <i class="ri-building-2-line text-xl text-cyan-400"></i>
              <div>
                <div class="font-semibold sv-text-primary">ผู้เช่า โควตา &amp; โมดูล</div>
                <div class="text-[11px] sv-text-muted">กำหนดแพ็กเกจ, GPU Priority, ระงับบริษัท</div>
              </div>
            </a>
            <a routerLink="/admin/admin-manage" class="p-3 rounded-xl border sv-border-subtle hover:border-cyan-400/50 transition flex items-center gap-3">
              <i class="ri-user-star-line text-xl text-violet-400"></i>
              <div>
                <div class="font-semibold sv-text-primary">บัญชี System Admin</div>
                <div class="text-[11px] sv-text-muted">จัดการสิทธิ์ผู้ดูแลระบบสูงสุด</div>
              </div>
            </a>
            <a routerLink="/admin/system-setting" class="p-3 rounded-xl border sv-border-subtle hover:border-cyan-400/50 transition flex items-center gap-3">
              <i class="ri-settings-4-line text-xl text-emerald-400"></i>
              <div>
                <div class="font-semibold sv-text-primary">ตั้งค่าระบบกลาง &amp; TTS</div>
                <div class="text-[11px] sv-text-muted">นโยบายความปลอดภัยและค่าเริ่มต้น</div>
              </div>
            </a>
            <a routerLink="/admin/error-logs" class="p-3 rounded-xl border sv-border-subtle hover:border-cyan-400/50 transition flex items-center gap-3">
              <i class="ri-bug-line text-xl text-rose-400"></i>
              <div>
                <div class="font-semibold sv-text-primary">System Error Logs</div>
                <div class="text-[11px] sv-text-muted">ติดตามข้อผิดพลาด API ข้ามบริษัท</div>
              </div>
            </a>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class PlatformInfrastructureComponent implements OnInit, OnDestroy {
  loading = false;
  ready: ReadyPayload | null = null;
  lastUpdated: Date | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.refresh();
    this.pollTimer = setInterval(() => this.refresh(false), 15000);
  }

  ngOnDestroy(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  get gpuDevicesLabel(): string {
    const devs = this.ready?.queue?.devices;
    if (!devs || !devs.length) return 'CPU / N/A';
    return devs.join(', ');
  }

  get queueKinds(): Array<{ key: string; value: number }> {
    const map = this.ready?.queue?.pendingByKind || {
      checkin: 0,
      identify: 0,
      detect: 0,
      cctv: 0,
      other: 0,
    };
    return Object.entries(map).map(([key, value]) => ({ key, value: Number(value || 0) }));
  }

  refresh(showLoading = true): void {
    if (showLoading) {
      this.loading = true;
      this.cdr.markForCheck();
    }
    this.http.get<ReadyPayload>('/ready').subscribe({
      next: (res) => {
        this.ready = res;
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
}
