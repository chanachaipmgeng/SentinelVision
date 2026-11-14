import { CommonModule } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { combineLatest } from 'rxjs';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';
import { SentinelApiService } from './sentinel-api.service';
import { SentinelOverview } from './sentinel.models';
import {
  EventsSection,
  LEGACY_TAB_REDIRECTS,
  SentinelTab,
  VisitorSection,
  WatchlistSection,
  WorkspaceSubNavItem,
  labelForWorkspace,
  normalizeAccessSection,
  normalizeEventsSection,
  normalizeVisitorSection,
  normalizeWatchlistSection,
  tabFromModuleSection,
  workspaceSubNav,
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
            class="btn-vault text-xs px-4 py-2 inline-flex items-center gap-1.5"
          >
            <i class="ri-camera-lens-line"></i> เปิดหน้าจอ Kiosk สด
          </a>
          <button
            type="button"
            class="ti-btn bg-slate-800/80 border border-white/10 text-slate-200 hover:text-white hover:border-cyan-500/40 text-xs px-3.5 py-2 rounded-full inline-flex items-center gap-1.5 transition-all"
            (click)="reloadOverview()"
          >
            <i class="ri-refresh-line" [class.animate-spin]="isLoading"></i> รีเฟรชข้อมูล
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
          <div *ngIf="moduleScoped" class="flex flex-wrap items-center justify-between gap-3 w-full">
            <div class="flex items-center gap-2 text-sm font-bold text-slate-100">
              <i class="ri-shield-star-line text-cyan-400 text-base"></i>
              <span>{{ moduleWorkspaceLabel }}</span>
            </div>
            <div class="flex flex-wrap items-center gap-2" *ngIf="subNavItems.length">
              <a
                *ngFor="let item of subNavItems"
                [routerLink]="item.route"
                class="ti-btn !rounded-full !px-3.5 !py-1.5 !text-xs !font-semibold transition-all duration-200 inline-flex items-center gap-1.5"
                [ngClass]="
                  currentSection === item.section
                    ? '!bg-gradient-to-r !from-cyan-500 !to-teal-500 !text-white !border-transparent !shadow-md !shadow-cyan-500/25'
                    : '!bg-white/5 hover:!bg-white/10 !text-slate-300 !border !border-white/10'
                "
              >
                <i [class]="item.icon"></i>
                <span>{{ item.label }}</span>
              </a>
            </div>
          </div>

          <span
            *ngIf="toastMessage"
            class="badge bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 px-3 py-1.5 text-xs font-semibold"
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
            [section]="watchlistSection"
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
            [section]="visitorSection"
            (toast)="showToast($event)"
            (overviewChanged)="reloadOverview()"
          ></app-sentinel-visitors-panel>
        </div>
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'events'">
          <app-sentinel-events-panel
            [section]="eventsSection"
            (toast)="showToast($event)"
            (overviewChanged)="reloadOverview()"
          ></app-sentinel-events-panel>
        </div>
        <div class="box-body space-y-6 sv-contain-region" *ngIf="activeTab === 'muster'">
          <app-sentinel-muster-panel [overview]="overview"></app-sentinel-muster-panel>
        </div>
      </div>
    </div>
  `
})
export class SentinelCenterComponent implements OnInit {
  companyId = '';
  activeTab: SentinelTab = 'command';
  moduleScoped = false;
  moduleWorkspaceLabel = '';
  currentSection = '';
  watchlistSection: WatchlistSection = 'identities';
  visitorSection: VisitorSection = 'passes';
  eventsSection: EventsSection = 'campaigns';
  subNavItems: WorkspaceSubNavItem[] = [];
  isLoading = false;
  toastMessage = '';
  overview: SentinelOverview | null = null;

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
          this.subNavItems = workspaceSubNav(workspace);
          if (workspace === 'ACCESS_CONTROL') {
            this.currentSection = normalizeAccessSection(section);
          } else if (workspace === 'WATCHLIST') {
            this.watchlistSection = normalizeWatchlistSection(section);
            this.currentSection = this.watchlistSection;
          } else if (workspace === 'VISITOR') {
            this.visitorSection = normalizeVisitorSection(section);
            this.currentSection = this.visitorSection;
          } else if (workspace === 'EVENTS') {
            this.eventsSection = normalizeEventsSection(section);
            this.currentSection = this.eventsSection;
          }
          return;
        }
        this.moduleScoped = false;
        this.subNavItems = [];
        this.currentSection = '';
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
