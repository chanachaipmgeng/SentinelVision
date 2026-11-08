import { StationMode } from '../../services/company-module-config.service';

/** URL path segment under `/company/scan/:stationMode`. */
export type StationModeSlug =
  | 'attendance'
  | 'access-control'
  | 'watchlist'
  | 'visitor'
  | 'event'
  | 'unified-hybrid';

const VALID_STATION_MODES: readonly StationMode[] = [
  'ATTENDANCE',
  'ACCESS_CONTROL',
  'WATCHLIST_MONITOR',
  'VISITOR_CHECKIN',
  'EVENT_CHECKIN',
  'UNIFIED_HYBRID',
];

const MODE_TO_SLUG: Record<StationMode, StationModeSlug> = {
  ATTENDANCE: 'attendance',
  ACCESS_CONTROL: 'access-control',
  WATCHLIST_MONITOR: 'watchlist',
  VISITOR_CHECKIN: 'visitor',
  EVENT_CHECKIN: 'event',
  UNIFIED_HYBRID: 'unified-hybrid',
};

const ALIASES: Record<string, StationMode> = {
  attendance: 'ATTENDANCE',
  'access-control': 'ACCESS_CONTROL',
  access_control: 'ACCESS_CONTROL',
  accesscontrol: 'ACCESS_CONTROL',
  watchlist: 'WATCHLIST_MONITOR',
  'watchlist-monitor': 'WATCHLIST_MONITOR',
  watchlist_monitor: 'WATCHLIST_MONITOR',
  visitor: 'VISITOR_CHECKIN',
  'visitor-checkin': 'VISITOR_CHECKIN',
  visitor_checkin: 'VISITOR_CHECKIN',
  event: 'EVENT_CHECKIN',
  'event-checkin': 'EVENT_CHECKIN',
  event_checkin: 'EVENT_CHECKIN',
  'unified-hybrid': 'UNIFIED_HYBRID',
  unified_hybrid: 'UNIFIED_HYBRID',
  hybrid: 'UNIFIED_HYBRID',
};

/**
 * Parse a route param or raw enum into a canonical StationMode.
 * Unknown / empty values fall back to ATTENDANCE (timestamp-face default).
 */
export function parseStationModeParam(param: string | null | undefined): StationMode {
  const raw = String(param || '').trim();
  if (!raw) {
    return 'ATTENDANCE';
  }
  const upper = raw.toUpperCase();
  if ((VALID_STATION_MODES as readonly string[]).includes(upper)) {
    return upper as StationMode;
  }
  return ALIASES[raw.toLowerCase()] || 'ATTENDANCE';
}

/** Resolved `:stationMode` + query context for modular `/company/scan/*` kiosks. */
export interface StationRouteContext {
  stationMode: StationMode;
  zoneId: string | null;
  eventId: string | null;
  /** True when the route path carried a `:stationMode` segment (not timestamp-face). */
  routeHadMode: boolean;
  captureMessage: string;
}

/**
 * Pure route → station context mapping used by enroll-face on every SPA nav
 * between `/company/scan/:stationMode` (and legacy timestamp-face with no param).
 */
export function resolveStationRouteContext(
  stationModeParam: string | null | undefined,
  zoneId: string | null | undefined,
  eventId: string | null | undefined,
): StationRouteContext {
  const routeHadMode = !!String(stationModeParam || '').trim();
  const stationMode = parseStationModeParam(stationModeParam);
  return {
    stationMode,
    zoneId: zoneId || null,
    eventId: eventId || null,
    routeHadMode,
    captureMessage: stationModeCaptureHint(stationMode),
  };
}

export function stationModeToSlug(mode: StationMode): StationModeSlug {
  return MODE_TO_SLUG[mode] || 'attendance';
}

export interface ScanRouteQuery {
  zoneId?: string | null;
  eventId?: string | null;
}

/** Build `/company/scan/{slug}?zoneId=&eventId=` for hub launch links. */
export function buildScanRoute(mode: StationMode, query: ScanRouteQuery = {}): string {
  const path = `/company/scan/${stationModeToSlug(mode)}`;
  const params = new URLSearchParams();
  if (query.zoneId) {
    params.set('zoneId', String(query.zoneId));
  }
  if (query.eventId) {
    params.set('eventId', String(query.eventId));
  }
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

export function isAttendanceChrome(mode: StationMode): boolean {
  return mode === 'ATTENDANCE' || mode === 'UNIFIED_HYBRID';
}

export function isAccessChrome(mode: StationMode): boolean {
  return mode === 'ACCESS_CONTROL' || mode === 'UNIFIED_HYBRID';
}

export function isWatchlistChrome(mode: StationMode): boolean {
  return mode === 'WATCHLIST_MONITOR';
}

export function isVisitorChrome(mode: StationMode): boolean {
  return mode === 'VISITOR_CHECKIN';
}

export function isEventChrome(mode: StationMode): boolean {
  return mode === 'EVENT_CHECKIN';
}

/** Attendance / hybrid still respect geofence; pure access/watchlist/visitor/event do not. */
export function stationModeRequiresGps(mode: StationMode): boolean {
  return mode === 'ATTENDANCE' || mode === 'UNIFIED_HYBRID';
}

/**
 * Door relay fires when mode is UNIFIED_HYBRID / ACCESS_CONTROL, or ATTENDANCE with
 * `enableDoorRelayOnAttendance` (backend Phase 1).
 */
export function shouldEnableDoorRelay(
  mode: StationMode,
  enableDoorRelayOnAttendance: boolean | null | undefined,
): boolean {
  if (mode === 'UNIFIED_HYBRID' || mode === 'ACCESS_CONTROL') {
    return true;
  }
  return mode === 'ATTENDANCE' && !!enableDoorRelayOnAttendance;
}

export function stationModeTitle(mode: StationMode): string {
  switch (mode) {
    case 'ACCESS_CONTROL':
      return 'จุดสแกนหน้าประตู (Access Control)';
    case 'WATCHLIST_MONITOR':
      return 'กล้องเฝ้าระวัง & VIP';
    case 'VISITOR_CHECKIN':
      return 'จุดสแกนผู้มาติดต่อ';
    case 'EVENT_CHECKIN':
      return 'จุดสแกนงานอีเวนต์';
    case 'UNIFIED_HYBRID':
      return 'ลงเวลา + เปิดประตู (Hybrid)';
    case 'ATTENDANCE':
    default:
      return 'สแกนใบหน้าลงเวลา (Attendance)';
  }
}

export function stationModeCaptureHint(mode: StationMode): string {
  switch (mode) {
    case 'ACCESS_CONTROL':
      return 'โหมด Access — ตรวจสิทธิ์โซนและสั่งเปิดประตูเมื่อได้รับอนุญาต';
    case 'WATCHLIST_MONITOR':
      return 'โหมดเฝ้าระวัง — Walk-by screening สำหรับ Blacklist / VIP';
    case 'VISITOR_CHECKIN':
      return 'โหมดผู้มาติดต่อ — ยืนยันบัตร Visitor และอัปเดต Muster Roll';
    case 'EVENT_CHECKIN':
      return 'โหมดอีเวนต์ — เช็คอินผู้ร่วมงานและแสดงเลขที่นั่ง';
    case 'UNIFIED_HYBRID':
      return 'โหมด Hybrid — ลงเวลาพร้อมสั่งเปิดประตูในสแกนเดียว';
    case 'ATTENDANCE':
    default:
      return 'โหมด stream — WebSocket + คิว GPU ลงเวลาหลายคนแบบเรียลไทม์';
  }
}
