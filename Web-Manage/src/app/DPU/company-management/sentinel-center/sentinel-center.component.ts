import { CommonModule } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { combineLatest } from 'rxjs';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';
import { SentinelApiService } from './sentinel-api.service';
import {
  LEGACY_TAB_REDIRECTS,
  SentinelTab,
  labelForWorkspace,
  tabFromModuleSection,
} from './sentinel-routing';
import { SentinelAccessLogsPanelComponent } from './panels/sentinel-access-logs-panel.component';
import { SentinelAccessPanelComponent } from './panels/sentinel-access-panel.component';
import { SentinelCommandPanelComponent } from './panels/sentinel-command-panel.component';
import { SentinelEventsPanelComponent } from './panels/sentinel-events-panel.component';
import { SentinelKpiRowComponent } from './panels/sentinel-kpi-row.component';
import { SentinelMusterPanelComponent } from './panels/sentinel-muster-panel.component';
import { SentinelVisitorsPanelComponent } from './panels/sentinel-visitors-panel.component';
import { SentinelWatchlistPanelComponent } from './panels/sentinel-watchlist-panel.component';

/**
 * SentinelVision shell — KPI banner + workspace nav + panel host.
 * Module routes (`access-control|watchlist|visitors|events/:section`) still load this shell
 * with `moduleWorkspace` data; panels own their tab logic.
 */
@Component({
  selector: 'app-sentinel-center',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    SharedModule,
    SentinelKpiRowComponent,
    SentinelCommandPanelComponent,
    SentinelWatchlistPanelComponent,
    SentinelAccessPanelComponent,
    SentinelAccessLogsPanelComponent,
    SentinelVisitorsPanelComponent,
    SentinelEventsPanelComponent,
    SentinelMusterPanelComponent,
  ],
  template: `
    <app-page-header
      [title]="'SentinelVision — ศูนย์ควบคุมอัตลักษณ์ ความปลอดภัย Access Control & Smart Events'"
      [activeTitle]="'SentinelVision Command'"
      [title1]="'Security, Access, Watchlist & Events'"
    ></app-page-header>

    <div class="space-y-6">
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
            (click)="reloadOverview()"
          >
            <i class="ri-refresh-line me-1" [class.animate-spin]="isLoading"></i> รีเฟรชข้อมูล
          </button>
        </div>
      </div>

      <app-sentinel-kpi-row [overview]="overview"></app-sentinel-kpi-row>

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

        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'command'">
          <app-sentinel-command-panel
            (toast)="showToast($event)"
            (overviewChanged)="reloadOverview()"
          ></app-sentinel-command-panel>
        </div>
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'watchlist'">
          <app-sentinel-watchlist-panel
            (toast)="showToast($event)"
            (overviewChanged)="reloadOverview()"
          ></app-sentinel-watchlist-panel>
        </div>
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'access'">
          <app-sentinel-access-panel
            section="zones"
            (toast)="showToast($event)"
            (overviewChanged)="reloadOverview()"
          ></app-sentinel-access-panel>
        </div>
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'access-logs'">
          <app-sentinel-access-logs-panel
            (toast)="showToast($event)"
            (overviewChanged)="reloadOverview()"
          ></app-sentinel-access-logs-panel>
        </div>
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'access-settings'">
          <app-sentinel-access-panel
            section="settings"
            (toast)="showToast($event)"
            (overviewChanged)="reloadOverview()"
          ></app-sentinel-access-panel>
        </div>
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'visitors'">
          <app-sentinel-visitors-panel
            (toast)="showToast($event)"
            (overviewChanged)="reloadOverview()"
          ></app-sentinel-visitors-panel>
        </div>
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'events'">
          <app-sentinel-events-panel
            (toast)="showToast($event)"
            (overviewChanged)="reloadOverview()"
          ></app-sentinel-events-panel>
        </div>
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'muster'">
          <app-sentinel-muster-panel [overview]="overview"></app-sentinel-muster-panel>
        </div>
      </div>
    </div>
  `,
})
export class SentinelCenterComponent implements OnInit {
  companyId = '';
  activeTab: SentinelTab = 'command';
  moduleScoped = false;
  moduleWorkspaceLabel = '';
  isLoading = false;
  toastMessage = '';
  overview: any = null;

  private readonly destroyRef = inject(DestroyRef);

  constructor(
    private api: SentinelApiService,
    private tokenService: TokenService,
    private route: ActivatedRoute,
    private router: Router,
  ) {}

  ngOnInit(): void {
    const company = this.tokenService.getSelectCompany();
    this.companyId = company?.companyId || '';

    // Subscribe so /access-control/zones ↔ logs ↔ settings flips without full remount.
    combineLatest([this.route.data, this.route.paramMap, this.route.queryParamMap])
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(([data, params, query]) => {
        const workspace = data['moduleWorkspace'] as string | undefined;
        const section = params.get('section');
        const mapped = tabFromModuleSection(workspace, section);
        if (mapped) {
          this.moduleScoped = true;
          this.activeTab = mapped;
          this.moduleWorkspaceLabel = labelForWorkspace(workspace!, section);
          return;
        }
        this.moduleScoped = false;
        const tab = query.get('tab');
        if (tab && LEGACY_TAB_REDIRECTS[tab]) {
          this.router.navigateByUrl(LEGACY_TAB_REDIRECTS[tab], { replaceUrl: true });
        }
      });

    if (this.companyId) {
      this.reloadOverview();
    }
  }

  setTab(tab: SentinelTab): void {
    if (this.moduleScoped) return;
    this.activeTab = tab;
  }

  showToast(msg: string): void {
    this.toastMessage = msg;
    setTimeout(() => {
      if (this.toastMessage === msg) this.toastMessage = '';
    }, 4000);
  }

  reloadOverview(): void {
    if (!this.companyId) return;
    this.isLoading = true;
    this.api.getOverview(this.companyId).subscribe({
      next: (res) => {
        this.overview = res;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      },
    });
  }
}
