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
      return 'station.access';
    case 'WATCHLIST_MONITOR':
      return 'station.watchlist';
    case 'VISITOR_CHECKIN':
      return 'station.visitor';
    case 'EVENT_CHECKIN':
      return 'station.event';
    case 'UNIFIED_HYBRID':
      return 'station.hybrid';
    case 'ATTENDANCE':
    default:
      return 'station.attendance';
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

/** Empty-feed hint under the camera — must not say ลงเวลา for non-attendance modes. */
export function stationModeEmptyHint(mode: StationMode): string {
  switch (mode) {
    case 'ACCESS_CONTROL':
      return 'ให้พนักงานเดินผ่านกล้องเพื่อตรวจสิทธิ์ประตู';
    case 'WATCHLIST_MONITOR':
      return 'ให้เดินผ่านกล้องเพื่อคัดกรอง Blacklist / VIP';
    case 'VISITOR_CHECKIN':
      return 'ให้ผู้มาติดต่อเดินผ่านกล้องเพื่อยืนยันบัตร';
    case 'EVENT_CHECKIN':
      return 'ให้ผู้ร่วมงานเดินผ่านกล้องเพื่อเช็คอินงาน';
    case 'UNIFIED_HYBRID':
      return 'ให้พนักงานเดินผ่านกล้องเพื่อลงเวลาและเปิดประตู';
    case 'ATTENDANCE':
    default:
      return 'ให้พนักงานเดินผ่านกล้องเพื่อลงเวลา';
  }
}

export function stationModeDeniedLabel(mode: StationMode): string {
  switch (mode) {
    case 'ACCESS_CONTROL':
      return 'ปฏิเสธสิทธิ์โซน';
    case 'WATCHLIST_MONITOR':
      return 'พบรายการเฝ้าระวัง';
    case 'VISITOR_CHECKIN':
      return 'บัตรผู้มาติดต่อไม่ผ่าน';
    case 'EVENT_CHECKIN':
      return 'เช็คอินงานไม่สำเร็จ';
    case 'UNIFIED_HYBRID':
    case 'ATTENDANCE':
    default:
      return 'ไม่สามารถลงเวลาได้';
  }
}

export function stationModeDeniedMessage(mode: StationMode): string {
  switch (mode) {
    case 'ACCESS_CONTROL':
      return 'ปฏิเสธสิทธิ์โซน — กรุณาติดต่อเจ้าหน้าที่';
    case 'WATCHLIST_MONITOR':
      return 'พบรายการเฝ้าระวัง — แจ้งเจ้าหน้าที่แล้ว';
    case 'VISITOR_CHECKIN':
      return 'บัตรผู้มาติดต่อไม่ผ่าน — กรุณาติดต่อโฮสต์';
    case 'EVENT_CHECKIN':
      return 'เช็คอินงานไม่สำเร็จ — ตรวจสอบรายชื่อผู้ร่วมงาน';
    case 'UNIFIED_HYBRID':
    case 'ATTENDANCE':
    default:
      return 'ไม่สามารถลงเวลาได้ กรุณาติดต่อเจ้าหน้าที่';
  }
}

/** Short verb for HUD / track overlay while a scan is in flight. */
export function stationModeBusyLabel(mode: StationMode): string {
  switch (mode) {
    case 'ACCESS_CONTROL':
      return 'กำลังตรวจสิทธิ์';
    case 'WATCHLIST_MONITOR':
      return 'กำลังคัดกรอง';
    case 'VISITOR_CHECKIN':
      return 'กำลังเช็คอินผู้มาติดต่อ';
    case 'EVENT_CHECKIN':
      return 'กำลังเช็คอินงาน';
    case 'UNIFIED_HYBRID':
      return 'กำลังลงเวลา/เปิดประตู';
    case 'ATTENDANCE':
    default:
      return 'กำลังลงเวลา';
  }
}

export function stationModeBusyCountLabel(mode: StationMode, busyCount: number): string {
  const n = Math.max(0, Math.floor(busyCount));
  switch (mode) {
    case 'ACCESS_CONTROL':
      return `กำลังตรวจสิทธิ์ ${n} คน`;
    case 'WATCHLIST_MONITOR':
      return `กำลังคัดกรอง ${n} คน`;
    case 'VISITOR_CHECKIN':
      return `กำลังเช็คอินผู้มาติดต่อ ${n} คน`;
    case 'EVENT_CHECKIN':
      return `กำลังเช็คอินงาน ${n} คน`;
    case 'UNIFIED_HYBRID':
      return `กำลังลงเวลา/เปิดประตู ${n} คน`;
    case 'ATTENDANCE':
    default:
      return `กำลังลงเวลา ${n} คน`;
  }
}

export type StationOutcomeKind = 'success' | 'duplicate' | 'denied' | 'warning';

export interface StationOutcomeInput {
  decision?: string | null;
  accessGranted?: boolean | null;
  identityType?: string | null;
  welcomeMessage?: string | null;
  seatNumber?: string | number | null;
  /** Pre-built attendance punch label (เข้างาน / ออกงาน / …). */
  attendanceLabel?: string | null;
}

/**
 * Result badge / toast label for a completed scan.
 * Non-attendance modes must never fall back to ลงเวลา* copy.
 */
export function stationModeOutcomeLabel(
  mode: StationMode,
  kind: StationOutcomeKind,
  input: StationOutcomeInput = {},
): string {
  const decision = String(input.decision || '').toUpperCase();
  const identity = String(input.identityType || '').toUpperCase();
  const welcome = String(input.welcomeMessage || '').trim();
  const seat =
    input.seatNumber != null && input.seatNumber !== ''
      ? String(input.seatNumber)
      : '';

  if (isAttendanceChrome(mode)) {
    if (kind === 'denied') {
      return stationModeDeniedLabel(mode);
    }
    if (input.attendanceLabel) {
      return input.attendanceLabel;
    }
    if (kind === 'duplicate') {
      return 'ลงเวลาไปแล้ว';
    }
    if (kind === 'warning') {
      return 'Warning — นอกพื้นที่';
    }
    return mode === 'UNIFIED_HYBRID' ? 'ลงเวลา + เปิดประตู' : 'ลงเวลาเข้างาน';
  }

  switch (mode) {
    case 'ACCESS_CONTROL': {
      if (kind === 'denied' || decision === 'ACCESS_DENIED' || input.accessGranted === false) {
        return 'ปฏิเสธสิทธิ์โซน';
      }
      if (kind === 'duplicate') {
        return 'ผ่านโซนแล้ว';
      }
      if (decision === 'ACCESS_GRANTED' || input.accessGranted === true) {
        return 'อนุญาตผ่าน / เปิดประตู';
      }
      return kind === 'warning' ? 'บันทึกแล้ว (เตือน)' : 'อนุญาตผ่าน';
    }
    case 'WATCHLIST_MONITOR': {
      if (kind === 'denied' || decision === 'ACCESS_DENIED') {
        return 'พบรายการเฝ้าระวัง';
      }
      if (identity === 'VIP' || decision === 'VIP_GREET') {
        return welcome || 'VIP Arrival';
      }
      if (kind === 'duplicate') {
        return 'ตรวจแล้ว';
      }
      return welcome || 'พบรายชื่อเฝ้าระวัง';
    }
    case 'VISITOR_CHECKIN': {
      if (kind === 'denied') {
        return 'บัตรผู้มาติดต่อไม่ผ่าน';
      }
      if (kind === 'duplicate') {
        return 'เช็คอินผู้มาติดต่อแล้ว';
      }
      return welcome || 'เช็คอินผู้มาติดต่อ';
    }
    case 'EVENT_CHECKIN': {
      if (kind === 'denied') {
        return 'ไม่อยู่ในรายชื่องาน';
      }
      if (kind === 'duplicate') {
        return 'เช็คอินงานแล้ว';
      }
      if (seat) {
        return welcome ? `${welcome} · ที่นั่ง ${seat}` : `เช็คอินงาน · ที่นั่ง ${seat}`;
      }
      return welcome || 'เช็คอินงาน';
    }
    default:
      return kind === 'duplicate' ? 'บันทึกแล้ว' : 'สำเร็จ';
  }
}

/** TTS template key for station outcome (non-attendance keys avoid ลงเวลา defaults). */
export type StationTtsKind = 'success' | 'warning' | 'duplicate';

export function stationModeTtsKey(
  mode: StationMode,
  kind: StationTtsKind,
):
  | 'checkInSuccess'
  | 'checkInWarning'
  | 'checkInDuplicate'
  | 'accessSuccess'
  | 'accessDuplicate'
  | 'watchlistSuccess'
  | 'watchlistDuplicate'
  | 'visitorSuccess'
  | 'visitorDuplicate'
  | 'eventSuccess'
  | 'eventDuplicate' {
  if (isAttendanceChrome(mode)) {
    if (kind === 'warning') return 'checkInWarning';
    if (kind === 'duplicate') return 'checkInDuplicate';
    return 'checkInSuccess';
  }
  switch (mode) {
    case 'ACCESS_CONTROL':
      return kind === 'duplicate' ? 'accessDuplicate' : 'accessSuccess';
    case 'WATCHLIST_MONITOR':
      return kind === 'duplicate' ? 'watchlistDuplicate' : 'watchlistSuccess';
    case 'VISITOR_CHECKIN':
      return kind === 'duplicate' ? 'visitorDuplicate' : 'visitorSuccess';
    case 'EVENT_CHECKIN':
      return kind === 'duplicate' ? 'eventDuplicate' : 'eventSuccess';
    default:
      return kind === 'duplicate' ? 'checkInDuplicate' : 'checkInSuccess';
  }
}
