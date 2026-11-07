import {
  CompanyModuleConfig,
  ScanActionRules,
  StationMode,
  TOGGLEABLE_COMPANY_MODULES,
  ToggleableCompanyModule,
} from '../../services/company-module-config.service';
import { buildScanRoute, stationModeTitle } from './scan-station-mode';

export interface HubModuleCard {
  module: ToggleableCompanyModule;
  label: string;
  hint: string;
  icon: string;
  /** Station mode launched from this card (null for modules without a live scanner). */
  stationMode: StationMode | null;
  enabled: boolean;
}

export interface HubLaunchLink {
  stationMode: StationMode;
  label: string;
  route: string;
  needsZone: boolean;
  needsEvent: boolean;
  module: ToggleableCompanyModule | 'HYBRID';
}

const MODULE_META: Record<
  ToggleableCompanyModule,
  { label: string; hint: string; icon: string; stationMode: StationMode | null }
> = {
  ATTENDANCE: {
    label: 'ลงเวลาทำงาน',
    hint: 'จุดสแกน Hybrid / Check-In / Check-Out',
    icon: 'ri-time-line',
    stationMode: 'ATTENDANCE',
  },
  ACCESS_CONTROL: {
    label: 'ควบคุมประตู',
    hint: 'ตรวจสิทธิ์โซนและสั่งเปิด Relay',
    icon: 'ri-door-lock-line',
    stationMode: 'ACCESS_CONTROL',
  },
  WATCHLIST: {
    label: 'เฝ้าระวัง & VIP',
    hint: 'Walk-by screening Blacklist / VIP',
    icon: 'ri-alarm-warning-line',
    stationMode: 'WATCHLIST_MONITOR',
  },
  VISITOR: {
    label: 'ผู้มาติดต่อ',
    hint: 'ยืนยันบัตร Visitor และ Muster Roll',
    icon: 'ri-user-shared-line',
    stationMode: 'VISITOR_CHECKIN',
  },
  EVENTS: {
    label: 'งานอีเวนต์',
    hint: 'เช็คอินผู้ร่วมงานและเลขที่นั่ง',
    icon: 'ri-calendar-event-line',
    stationMode: 'EVENT_CHECKIN',
  },
};

/** Toggle a pluggable module on/off; always-on modules are ignored. */
export function toggleEnabledModule(
  enabled: readonly string[],
  module: ToggleableCompanyModule,
  on: boolean,
): ToggleableCompanyModule[] {
  const set = new Set(
    enabled.filter((m) =>
      (TOGGLEABLE_COMPANY_MODULES as readonly string[]).includes(m),
    ) as ToggleableCompanyModule[],
  );
  if (on) {
    set.add(module);
  } else {
    set.delete(module);
  }
  return TOGGLEABLE_COMPANY_MODULES.filter((m) => set.has(m));
}

export function buildHubModuleCards(config: CompanyModuleConfig): HubModuleCard[] {
  const enabled = new Set(config.enabledModules);
  return TOGGLEABLE_COMPANY_MODULES.map((module) => {
    const meta = MODULE_META[module];
    return {
      module,
      label: meta.label,
      hint: meta.hint,
      icon: meta.icon,
      stationMode: meta.stationMode,
      enabled: enabled.has(module),
    };
  });
}

/**
 * Launch links for enabled scanners + UNIFIED_HYBRID when both attendance and
 * access-control are on (or hybrid is the default station mode).
 */
export function buildHubLaunchLinks(
  config: CompanyModuleConfig,
  opts: { zoneId?: string | null; eventId?: string | null } = {},
): HubLaunchLink[] {
  const enabled = new Set(config.enabledModules);
  const zoneId = opts.zoneId ?? config.defaultZoneId;
  const eventId = opts.eventId ?? config.defaultEventId;
  const links: HubLaunchLink[] = [];

  const push = (
    stationMode: StationMode,
    module: ToggleableCompanyModule | 'HYBRID',
    needsZone: boolean,
    needsEvent: boolean,
  ) => {
    links.push({
      stationMode,
      label: stationModeTitle(stationMode),
      route: buildScanRoute(stationMode, { zoneId, eventId }),
      needsZone,
      needsEvent,
      module,
    });
  };

  if (enabled.has('ATTENDANCE')) {
    push('ATTENDANCE', 'ATTENDANCE', false, false);
  }
  if (enabled.has('ACCESS_CONTROL')) {
    push('ACCESS_CONTROL', 'ACCESS_CONTROL', true, false);
  }
  if (enabled.has('WATCHLIST')) {
    push('WATCHLIST_MONITOR', 'WATCHLIST', false, false);
  }
  if (enabled.has('VISITOR')) {
    push('VISITOR_CHECKIN', 'VISITOR', true, false);
  }
  if (enabled.has('EVENTS')) {
    push('EVENT_CHECKIN', 'EVENTS', false, true);
  }

  const wantHybrid =
    config.defaultStationMode === 'UNIFIED_HYBRID' ||
    (enabled.has('ATTENDANCE') && enabled.has('ACCESS_CONTROL'));
  if (wantHybrid) {
    push('UNIFIED_HYBRID', 'HYBRID', true, false);
  }

  return links;
}

/** Body for PUT `/sentinel/company/{id}/module-config` (Phase 2 service). */
export function buildModuleConfigPutBody(
  draft: CompanyModuleConfig,
): Partial<CompanyModuleConfig> {
  return {
    enabledModules: [...draft.enabledModules],
    defaultStationMode: draft.defaultStationMode,
    defaultZoneId: draft.defaultZoneId,
    defaultEventId: draft.defaultEventId,
    scanActionRules: { ...draft.scanActionRules },
    moduleSettings: { ...draft.moduleSettings },
  };
}

export function patchScanActionRule<K extends keyof ScanActionRules>(
  rules: ScanActionRules,
  key: K,
  value: ScanActionRules[K],
): ScanActionRules {
  return { ...rules, [key]: value };
}

/** Deep-link from company home → hub (optionally open a specific scanner). */
export function companyHomeScanHubLink(companyId: string, openMode?: StationMode | null): string {
  const base = `/company/scan-hub`;
  if (!openMode) {
    return base;
  }
  return `${base}?launch=${encodeURIComponent(openMode)}`;
}

export { MODULE_META };
