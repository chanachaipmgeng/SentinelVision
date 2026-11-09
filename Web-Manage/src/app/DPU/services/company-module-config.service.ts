import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map, shareReplay, tap } from 'rxjs/operators';

/** Always-on platform modules (never toggled off). */
export const ALWAYS_ON_MODULES = ['CORE', 'GOVERNANCE'] as const;

/** Modules a company admin can enable/disable. */
export const TOGGLEABLE_COMPANY_MODULES = [
  'ATTENDANCE',
  'ACCESS_CONTROL',
  'WATCHLIST',
  'VISITOR',
  'EVENTS',
  'CCTV',
] as const;

export type AlwaysOnModule = (typeof ALWAYS_ON_MODULES)[number];
export type ToggleableCompanyModule = (typeof TOGGLEABLE_COMPANY_MODULES)[number];
export type PlatformModule = AlwaysOnModule | ToggleableCompanyModule;

export type StationMode =
  | 'ATTENDANCE'
  | 'ACCESS_CONTROL'
  | 'WATCHLIST_MONITOR'
  | 'VISITOR_CHECKIN'
  | 'EVENT_CHECKIN'
  | 'UNIFIED_HYBRID';

export const VALID_STATION_MODES: readonly StationMode[] = [
  'ATTENDANCE',
  'ACCESS_CONTROL',
  'WATCHLIST_MONITOR',
  'VISITOR_CHECKIN',
  'EVENT_CHECKIN',
  'UNIFIED_HYBRID',
] as const;

export type UnknownFaceAction = 'IGNORE' | 'LOG_INCIDENT';

export interface ScanActionRules {
  enableBlacklistSilentAlarm: boolean;
  enableVipGreeting: boolean;
  enableTtsVoice: boolean;
  enableDoorRelayOnAttendance: boolean;
  unknownFaceAction: UnknownFaceAction;
}

export interface CompanyModuleSettings {
  attendance?: { defaultPunchMode?: string; requireGps?: boolean };
  accessControl?: { autoLockSeconds?: number; require2FA?: boolean };
  watchlist?: { silentAlarmOnPoi?: boolean };
  visitor?: { defaultPassHours?: number };
  events?: { showSeatFullscreen?: boolean; autoExpireDays?: number };
}

export interface CompanyModuleConfig {
  enabledModules: ToggleableCompanyModule[];
  alwaysOnModules: AlwaysOnModule[];
  defaultStationMode: StationMode;
  defaultZoneId: string | null;
  defaultEventId: string | null;
  scanActionRules: ScanActionRules;
  moduleSettings: CompanyModuleSettings;
}

export const DEFAULT_COMPANY_MODULE_CONFIG: CompanyModuleConfig = {
  // Spreads all toggleable modules including CCTV (Phase 3).
  enabledModules: [...TOGGLEABLE_COMPANY_MODULES],
  alwaysOnModules: [...ALWAYS_ON_MODULES],
  defaultStationMode: 'ATTENDANCE',
  defaultZoneId: null,
  defaultEventId: null,
  scanActionRules: {
    enableBlacklistSilentAlarm: true,
    enableVipGreeting: true,
    enableTtsVoice: true,
    enableDoorRelayOnAttendance: false,
    unknownFaceAction: 'IGNORE',
  },
  moduleSettings: {
    attendance: { defaultPunchMode: 'AUTO', requireGps: true },
    accessControl: { autoLockSeconds: 5, require2FA: false },
    watchlist: { silentAlarmOnPoi: true },
    visitor: { defaultPassHours: 12 },
    events: { showSeatFullscreen: true },
  },
};

function normalizeConfig(raw: Partial<CompanyModuleConfig> | null | undefined): CompanyModuleConfig {
  const base = DEFAULT_COMPANY_MODULE_CONFIG;
  const enabled = Array.isArray(raw?.enabledModules)
    ? (raw!.enabledModules.filter((m) =>
        (TOGGLEABLE_COMPANY_MODULES as readonly string[]).includes(m)
      ) as ToggleableCompanyModule[])
    : [...base.enabledModules];

  return {
    enabledModules: enabled,
    alwaysOnModules: [...ALWAYS_ON_MODULES],
    defaultStationMode: (raw?.defaultStationMode as StationMode) || base.defaultStationMode,
    defaultZoneId: raw?.defaultZoneId ?? null,
    defaultEventId: raw?.defaultEventId ?? null,
    scanActionRules: {
      ...base.scanActionRules,
      ...(raw?.scanActionRules || {}),
    },
    moduleSettings: {
      ...base.moduleSettings,
      ...(raw?.moduleSettings || {}),
    },
  };
}

/**
 * Typed client for GET/PUT `/sentinel/company/{id}/module-config`.
 * Caches per companyId. Falls back to defaults when the endpoint is not yet deployed.
 */
@Injectable({
  providedIn: 'root',
})
export class CompanyModuleConfigService {
  private readonly cache = new Map<string, CompanyModuleConfig>();
  private readonly inflight = new Map<string, Observable<CompanyModuleConfig>>();

  constructor(private http: HttpClient) {}

  getModuleConfig(companyId: string, forceRefresh = false): Observable<CompanyModuleConfig> {
    if (!companyId) {
      return of({ ...DEFAULT_COMPANY_MODULE_CONFIG });
    }

    if (!forceRefresh && this.cache.has(companyId)) {
      return of(this.cache.get(companyId)!);
    }

    if (!forceRefresh && this.inflight.has(companyId)) {
      return this.inflight.get(companyId)!;
    }

    const req$ = this.http
      .get<Partial<CompanyModuleConfig>>(`/sentinel/company/${companyId}/module-config`)
      .pipe(
        map((raw) => normalizeConfig(raw)),
        tap((cfg) => {
          this.cache.set(companyId, cfg);
          this.inflight.delete(companyId);
        }),
        catchError(() => {
          const fallback = { ...DEFAULT_COMPANY_MODULE_CONFIG };
          this.cache.set(companyId, fallback);
          this.inflight.delete(companyId);
          return of(fallback);
        }),
        shareReplay(1)
      );

    this.inflight.set(companyId, req$);
    return req$;
  }

  updateModuleConfig(
    companyId: string,
    body: Partial<CompanyModuleConfig>
  ): Observable<CompanyModuleConfig> {
    return this.http
      .put<Partial<CompanyModuleConfig>>(`/sentinel/company/${companyId}/module-config`, body)
      .pipe(
        map((raw) => normalizeConfig(raw)),
        tap((cfg) => this.cache.set(companyId, cfg))
      );
  }

  /** Effective modules for nav filtering (always-on + enabled). */
  getEffectiveModules(companyId: string): Observable<string[]> {
    return this.getModuleConfig(companyId).pipe(
      map((cfg) => [
        ...ALWAYS_ON_MODULES,
        ...cfg.enabledModules,
      ])
    );
  }

  clearCache(companyId?: string): void {
    if (companyId) {
      this.cache.delete(companyId);
      this.inflight.delete(companyId);
    } else {
      this.cache.clear();
      this.inflight.clear();
    }
  }
}
