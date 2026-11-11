import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';
import {
  CompanyModuleConfig,
  CompanyModuleConfigService,
  DEFAULT_COMPANY_MODULE_CONFIG,
  StationMode,
  TOGGLEABLE_COMPANY_MODULES,
  ToggleableCompanyModule,
} from '../../services/company-module-config.service';
import {
  HubLaunchLink,
  HubModuleCard,
  buildHubLaunchLinks,
  buildHubModuleCards,
  buildModuleConfigPutBody,
  companyHomeScanHubLink,
  patchScanActionRule,
  toggleEnabledModule,
} from './scan-hub.helpers';
import { buildScanRoute, parseStationModeParam } from './scan-station-mode';

const STATION_MODES: StationMode[] = [
  'ATTENDANCE',
  'ACCESS_CONTROL',
  'WATCHLIST_MONITOR',
  'VISITOR_CHECKIN',
  'EVENT_CHECKIN',
  'UNIFIED_HYBRID',
];

/**
 * Full Scan & Action Hub — replaces the Phase 2 placeholder at `/company/scan-hub`.
 * Uses Phase 2 `CompanyModuleConfigService` (GET/PUT module-config).
 */
@Component({
    selector: 'app-scan-hub',
    imports: [
        CommonModule,
        FormsModule,
        RouterModule,
        SharedModule,
        PageToolbarComponent,
        StatChipComponent,
        EmptyStateComponent,
    ],
    templateUrl: './scan-hub.component.html',
    styleUrls: ['./scan-hub.component.scss']
})
export class ScanHubComponent implements OnInit {
  companyId = '';
  loading = true;
  saving = false;
  error: string | null = null;
  saveMessage: string | null = null;
  usedFallback = false;

  config: CompanyModuleConfig = cloneDefaultConfig();

  moduleCards: HubModuleCard[] = [];
  launchLinks: HubLaunchLink[] = [];

  zones: Array<{ zoneId: string; name: string }> = [];
  events: Array<{ eventId: string; name: string }> = [];

  readonly stationModes = STATION_MODES;
  readonly unknownFaceActions: Array<'IGNORE' | 'LOG_INCIDENT'> = ['IGNORE', 'LOG_INCIDENT'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private http: HttpClient,
    private tokenService: TokenService,
    private moduleConfig: CompanyModuleConfigService,
  ) {
    this.companyId =
      this.route.snapshot.paramMap.get('companyId') ||
      this.tokenService.getSelectCompany()?.companyId ||
      '';
  }

  ngOnInit(): void {
    if (!this.companyId) {
      this.loading = false;
      this.error = 'ไม่พบรหัสบริษัท — เลือกบริษัทจากหน้าหลักก่อน';
      return;
    }
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.error = null;
    this.saveMessage = null;
    this.usedFallback = false;
    this.moduleConfig.clearCache(this.companyId);

    this.moduleConfig.getModuleConfig(this.companyId, true).subscribe({
      next: (cfg) => {
        // Service falls back to defaults on 404 — detect that via a follow-up probe is overkill;
        // treat identical-to-default after error path as soft warning only when save fails later.
        this.applyConfig(cfg);
        this.loading = false;
        this.maybeAutoLaunch();
      },
      error: () => {
        this.applyConfig(cloneDefaultConfig());
        this.loading = false;
        this.usedFallback = true;
        this.error = 'โหลด module-config ไม่สำเร็จ — ใช้ค่าเริ่มต้นชั่วคราว';
        this.maybeAutoLaunch();
      },
    });

    this.http
      .get<Array<{ zoneId: string; name?: string; thName?: string }>>(
        `/sentinel/company/${this.companyId}/zones`,
      )
      .subscribe({
      next: (rows) => {
        this.zones = (rows || []).map((z) => ({
          zoneId: z.zoneId,
          name: String(z.name ?? z.thName ?? z.zoneId),
        }));
      },
      error: () => (this.zones = []),
    });
    this.http
      .get<Array<{ eventId: string; name?: string }>>(`/sentinel/company/${this.companyId}/events`)
      .subscribe({
      next: (rows) => {
        this.events = (rows || []).map((e) => ({
          eventId: e.eventId,
          name: String(e.name ?? e.eventId),
        }));
      },
      error: () => (this.events = []),
    });
  }

  private applyConfig(cfg: CompanyModuleConfig): void {
    this.config = {
      ...cfg,
      enabledModules: [...cfg.enabledModules],
      alwaysOnModules: [...cfg.alwaysOnModules],
      scanActionRules: { ...cfg.scanActionRules },
      moduleSettings: { ...(cfg.moduleSettings || {}) },
    };
    this.refreshDerived();
  }

  private refreshDerived(): void {
    this.moduleCards = buildHubModuleCards(this.config);
    this.launchLinks = buildHubLaunchLinks(this.config, {
      zoneId: this.config.defaultZoneId,
      eventId: this.config.defaultEventId,
    });
  }

  /** `?launch=ATTENDANCE` deep-link from company home. */
  private maybeAutoLaunch(): void {
    const launch = this.route.snapshot.queryParamMap.get('launch');
    if (!launch) {
      return;
    }
    const mode = parseStationModeParam(launch);
    const link = this.launchLinks.find((l) => l.stationMode === mode);
    if (link) {
      void this.router.navigateByUrl(link.route);
    }
  }

  setModuleEnabled(module: ToggleableCompanyModule, on: boolean): void {
    this.config.enabledModules = toggleEnabledModule(this.config.enabledModules, module, on);
    this.refreshDerived();
  }

  onDefaultStationModeChange(mode: StationMode): void {
    this.config.defaultStationMode = mode;
    this.refreshDerived();
  }

  onDefaultZoneChange(zoneId: string): void {
    this.config.defaultZoneId = zoneId || null;
    this.refreshDerived();
  }

  onDefaultEventChange(eventId: string): void {
    this.config.defaultEventId = eventId || null;
    this.refreshDerived();
  }

  setRule(
    key: keyof CompanyModuleConfig['scanActionRules'],
    value: boolean | 'IGNORE' | 'LOG_INCIDENT',
  ): void {
    this.config.scanActionRules = patchScanActionRule(
      this.config.scanActionRules,
      key,
      value as never,
    );
  }

  save(): void {
    if (!this.companyId || this.saving) {
      return;
    }
    this.saving = true;
    this.saveMessage = null;
    this.error = null;
    const body = buildModuleConfigPutBody(this.config);
    this.moduleConfig.updateModuleConfig(this.companyId, body).subscribe({
      next: (cfg) => {
        this.applyConfig(cfg);
        this.saving = false;
        this.usedFallback = false;
        this.saveMessage = 'บันทึกการตั้งค่าโมดูลแล้ว';
      },
      error: (err) => {
        this.saving = false;
        this.error =
          err?.error?.detail ||
          'บันทึกไม่สำเร็จ — ตรวจว่า backend รองรับ PUT /module-config แล้วหรือยัง';
      },
    });
  }

  launch(link: HubLaunchLink): void {
    void this.router.navigateByUrl(
      buildScanRoute(link.stationMode, {
        zoneId: this.config.defaultZoneId,
        eventId: this.config.defaultEventId,
      }),
    );
  }

  openLegacyKiosk(): void {
    void this.router.navigateByUrl('/company/timestamp-face');
  }

  homeLink(): string {
    return this.companyId ? `/company/home/${this.companyId}` : '/company/dashboard';
  }

  static hubPathForCompany(companyId: string, launch?: StationMode | null): string {
    return companyHomeScanHubLink(companyId, launch);
  }

  trackModule(_: number, card: HubModuleCard): string {
    return card.module;
  }

  trackLaunch(_: number, link: HubLaunchLink): string {
    return link.stationMode;
  }

  get enabledCount(): number {
    return this.config.enabledModules.length;
  }

  get toggleableCount(): number {
    return TOGGLEABLE_COMPANY_MODULES.length;
  }
}

function cloneDefaultConfig(): CompanyModuleConfig {
  return {
    ...DEFAULT_COMPANY_MODULE_CONFIG,
    enabledModules: [...DEFAULT_COMPANY_MODULE_CONFIG.enabledModules],
    alwaysOnModules: [...DEFAULT_COMPANY_MODULE_CONFIG.alwaysOnModules],
    scanActionRules: { ...DEFAULT_COMPANY_MODULE_CONFIG.scanActionRules },
    moduleSettings: { ...DEFAULT_COMPANY_MODULE_CONFIG.moduleSettings },
  };
}
