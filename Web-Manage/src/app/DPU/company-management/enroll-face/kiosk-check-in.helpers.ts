import { TtsTemplateKey } from '../../../shared/utils/tts-templates';
import { StationMode } from '../../services/company-module-config.service';
import {
  stationModeBusyCountLabel,
  stationModeOutcomeLabel,
  stationModeTtsKey,
} from '../scan-hub/scan-station-mode';
import { SmoothBox, iou } from './overlay';

export type KioskPunchMode = 'AUTO' | 'CHECK_IN' | 'BREAK_OUT' | 'BREAK_IN' | 'CHECK_OUT';

export interface KioskWsDetectMessage {
  frameWidth?: number;
  frameHeight?: number;
  faces?: Array<Record<string, unknown>>;
  queue?: { pending?: number };
}

export interface CheckInMember {
  fullName?: string;
  firstName?: string;
  lastName?: string;
  memberId?: string;
  username?: string;
}

export interface CheckInEmployee {
  fullName?: string;
  firstName?: string;
  employeeId?: string;
  department?: string;
  position?: string;
  member?: CheckInMember;
}

export interface CheckInTimestamp {
  timestampType?: number | string;
  isLate?: boolean;
  lateMinutes?: number;
  overtimeMinutes?: number;
  timestamp?: string;
  photoTimestamp?: string | null;
  photoUrl?: string;
  locationName?: string;
  timestampId?: string;
}

/** HTTP identify / check-in / modular station payloads (shape varies by mode). */
export interface CheckInApiResponse {
  employee?: CheckInEmployee;
  member?: CheckInMember;
  timestamp?: CheckInTimestamp;
  subjectName?: string;
  memberId?: string;
  confidencePercent?: number;
  distance?: number;
  matchQuality?: string | null;
  isWarning?: boolean;
  accessGranted?: boolean;
  decision?: string;
  identityType?: string;
  welcomeMessage?: string;
  seatNumber?: string | number;
  duplicate?: boolean;
}

export interface CheckInFeedItem {
  id: string;
  employeeName: string;
  employeeId: string;
  department: string;
  position: string;
  statusLabel: string;
  statusKind: 'success' | 'warning' | 'error' | 'info';
  locationName: string;
  timestamp: Date;
  photoUrl: string | null;
  message: string;
  confidencePercent?: number | null;
  matchQuality?: string | null;
  distance?: number | null;
  timestampType?: number;
  isLate?: boolean;
  lateMinutes?: number;
  overtimeMinutes?: number;
}

export interface KioskRosterPerson {
  company_employeeId: string;
  employeeId: string;
  employeeName: string;
  picture?: string | null;
  department?: string;
  position?: string;
  timestamp?: string | Date;
  timestampType?: number;
  locationName?: string;
  photoTimestamp?: string | null;
  approvalStatus?: string;
  isLate?: boolean;
  lateMinutes?: number;
  overtimeMinutes?: number;
}

export interface KioskAttendance {
  summary: {
    checkedInCount: number;
    inAreaCount: number;
    checkedOutCount?: number;
    outsideCount: number;
    lateCount?: number;
    day?: string;
  };
  checkedIn: KioskRosterPerson[];
}

export type TrackPhase = 'watching' | 'capturing' | 'checking_in' | 'done' | 'cooldown';

export interface FaceTrack {
  id: number;
  box: SmoothBox;
  /** Latest raw detection; render loop eases `box` toward this each frame. */
  targetBox: SmoothBox;
  firstSeenAt: number;
  lastSeenAt: number;
  label: string | null;
  memberId: string | null;
  confidence: number | null;
  phase: TrackPhase;
  lastIdentifyAt: number;
  identifyInFlight: boolean;
  captureFrames: string[];
  captureTimer: ReturnType<typeof setInterval> | null;
  retryAfter: number;
  statusText: string | null;
}

export function normalizeTimestampType(raw: number | string | undefined): number {
  if (typeof raw === 'number') return raw;
  if (typeof raw === 'string' && /^\d+$/.test(raw)) return Number(raw);
  if (raw === 'WARNING' || raw === 'Warning') return 0;
  if (raw === 'CHECK_OUT') return 2;
  if (raw === 'BREAK_OUT') return 4;
  if (raw === 'BREAK_IN') return 5;
  return 1;
}

export function resolveAttendanceLabel(params: {
  isWarning: boolean;
  tsTypeNum: number;
  isLate: boolean;
  lateMinutes: number;
  overtimeMinutes: number;
}): string {
  if (params.isWarning) return 'Warning — นอกพื้นที่';
  if (params.tsTypeNum === 2) {
    return params.overtimeMinutes > 0
      ? `ออกงาน (OT ${params.overtimeMinutes} นาที)`
      : 'ลงเวลาออกงาน';
  }
  if (params.tsTypeNum === 4) return 'พักนอก (Break-Out)';
  if (params.tsTypeNum === 5) return 'พักเข้า (Break-In)';
  if (params.isLate && params.lateMinutes > 0) {
    return `เข้างาน (สาย ${params.lateMinutes} นาที)`;
  }
  return 'ลงเวลาเข้างาน';
}

export interface StationHudUpdate {
  doorStatus?: 'unlocked' | 'denied';
  vipArrivalName?: string;
  welcomeBanner?: string;
  seatNumber?: string;
}

export function resolveStationModeHudUpdate(
  response: CheckInApiResponse | null | undefined,
  doorRelayEnabled: boolean,
): StationHudUpdate {
  const out: StationHudUpdate = {};
  if (!response) return out;

  if (response.accessGranted === true || response.decision === 'ACCESS_GRANTED') {
    out.doorStatus = 'unlocked';
  } else if (response.accessGranted === false || response.decision === 'ACCESS_DENIED') {
    out.doorStatus = 'denied';
  } else if (doorRelayEnabled && !response.duplicate) {
    out.doorStatus = 'unlocked';
  }

  const identityType = String(response.identityType || '').toUpperCase();
  if (identityType === 'VIP' || response.decision === 'VIP_GREET') {
    out.vipArrivalName =
      response.subjectName || response.employee?.fullName || response.member?.fullName || 'VIP';
  }
  if (response.welcomeMessage) {
    out.welcomeBanner = String(response.welcomeMessage);
  }
  if (response.seatNumber != null && response.seatNumber !== '') {
    out.seatNumber = String(response.seatNumber);
  }
  return out;
}

export interface CheckInFeedResolution {
  item: CheckInFeedItem;
  employeeName: string;
  firstName: string;
  employeeCode: string;
  memberId: string | null;
  confidencePercent: number;
  isWarning: boolean;
  outcomeKind: 'duplicate' | 'warning' | 'denied' | 'success';
  statusLabel: string;
  toastMessage: string;
  toastKind: 'success' | 'warning' | 'error' | 'info';
  speechKey: TtsTemplateKey;
}

export function buildCheckInFeedRecord(params: {
  response: CheckInApiResponse;
  frames: string[];
  trackLabel?: string | null;
  trackMemberId?: string | null;
  stationMode: StationMode;
  showAttendancePanel: boolean;
  isDuplicate: boolean;
  baseUrl: string;
  resolveAuthedImage: (file: string) => string;
}): CheckInFeedResolution {
  const { response, frames, stationMode, showAttendancePanel, isDuplicate, baseUrl } = params;
  const employee: CheckInEmployee = { ...(response.employee || {}) };
  const member: CheckInMember = response.member || employee.member || {};
  if (response.subjectName && !employee.fullName && !member.fullName) {
    employee.fullName = response.subjectName;
  }

  const ts = response.timestamp || {};
  const tsTypeNum = normalizeTimestampType(ts.timestampType);
  const isWarning = !!response.isWarning || tsTypeNum === 0;
  const isBreakOut = tsTypeNum === 4;
  const isBreakIn = tsTypeNum === 5;
  const isLate = !!ts.isLate;
  const lateMinutes = Number(ts.lateMinutes || 0);
  const overtimeMinutes = Number(ts.overtimeMinutes || 0);

  const employeeName =
    employee.fullName ||
    member.fullName ||
    `${member.firstName || ''} ${member.lastName || ''}`.trim() ||
    params.trackLabel ||
    'พนักงาน';
  const firstName = (
    member.firstName ||
    employee.firstName ||
    employeeName.split(/\s+/)[0] ||
    ''
  ).trim();
  const employeeCode = employee.employeeId || member.username || '';
  const confidencePercent = Number(
    response.confidencePercent ?? (1 - Number(response.distance || 0)) * 100,
  );
  const time = ts.timestamp ? new Date(ts.timestamp) : new Date();
  const timeLabel = time.toLocaleTimeString('th', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  const photoFile = ts.photoTimestamp || null;
  const photoUrl = photoFile
    ? params.resolveAuthedImage(photoFile)
    : frames.length
      ? frames[Math.floor(frames.length / 2)]
      : ts.photoUrl
        ? `${baseUrl || ''}${ts.photoUrl}`.replace(/([^:]\/)\/+/g, '$1')
        : null;

  const attendanceLabel = resolveAttendanceLabel({
    isWarning,
    tsTypeNum,
    isLate,
    lateMinutes,
    overtimeMinutes,
  });

  const outcomeKind: CheckInFeedResolution['outcomeKind'] = isDuplicate
    ? 'duplicate'
    : isWarning
      ? 'warning'
      : response.accessGranted === false ||
          String(response.decision || '').toUpperCase() === 'ACCESS_DENIED'
        ? 'denied'
        : 'success';

  const statusLabel = stationModeOutcomeLabel(stationMode, outcomeKind, {
    decision: response.decision,
    accessGranted: response.accessGranted,
    identityType: response.identityType,
    welcomeMessage: response.welcomeMessage,
    seatNumber: response.seatNumber,
    attendanceLabel: isDuplicate
      ? isWarning
        ? 'บันทึกแล้ว (Warning)'
        : 'ลงเวลาไปแล้ว'
      : attendanceLabel,
  });

  let statusKind: CheckInFeedItem['statusKind'] =
    outcomeKind === 'denied'
      ? 'error'
      : isWarning || isLate
        ? 'warning'
        : 'success';
  if (isBreakOut || isBreakIn || isDuplicate) {
    statusKind = 'info';
  }

  const item: CheckInFeedItem = {
    id: ts.timestampId || `${Date.now()}`,
    employeeName,
    employeeId: employee.employeeId || member.username || '-',
    department: employee.department || '-',
    position: employee.position || '-',
    statusLabel,
    statusKind,
    locationName:
      ts.locationName ||
      (isWarning && showAttendancePanel ? 'นอกพื้นที่ลงเวลา' : '-'),
    timestamp: time,
    photoUrl,
    message: `${employeeName} · ${timeLabel}`,
    confidencePercent: Number.isFinite(confidencePercent) ? confidencePercent : null,
    matchQuality: response.matchQuality ?? null,
    distance: response.distance != null ? Number(response.distance) : null,
    timestampType: tsTypeNum,
    isLate,
    lateMinutes,
    overtimeMinutes,
  };

  const speechKey: TtsTemplateKey = stationModeTtsKey(
    stationMode,
    isDuplicate ? 'duplicate' : isWarning ? 'warning' : 'success',
  );

  const toastMessage = isDuplicate
    ? `${employeeName} ${statusLabel} (ไม่บันทึกซ้ำ)`
    : isWarning
      ? `Warning: ${employeeName} (${item.confidencePercent?.toFixed(1) ?? '-'}%)`
      : `${statusLabel}: ${employeeName} (${item.confidencePercent?.toFixed(1) ?? '-'}%)`;

  const toastKind: CheckInFeedResolution['toastKind'] = isDuplicate
    ? 'info'
    : isWarning || outcomeKind === 'denied'
      ? 'warning'
      : 'success';

  return {
    item,
    employeeName,
    firstName,
    employeeCode,
    memberId: response.memberId || member.memberId || params.trackMemberId || null,
    confidencePercent,
    isWarning,
    outcomeKind,
    statusLabel,
    toastMessage,
    toastKind,
    speechKey,
  };
}

export function buildKioskStatusMessage(state: {
  adminPreviewMode: boolean;
  cameraFailed: boolean;
  cameraRecoveryTitle: string;
  gpsRequired: boolean;
  hasValidLocation: boolean;
  errorMessage: string | null;
  tracks: ReadonlyArray<{ label: string | null }>;
  wsConnected: boolean;
  serverDetectActive: boolean;
  checkingInCount: number;
  stationMode: StationMode;
  queuePending: number;
}): string {
  if (state.adminPreviewMode) {
    return 'Admin preview — ไม่มีกล้อง; ตรวจ layout / status pills ได้';
  }
  if (state.cameraFailed) {
    return state.cameraRecoveryTitle || 'ไม่สามารถเปิดกล้องได้ — ดูขั้นตอนด้านล่าง';
  }
  if (state.gpsRequired && !state.hasValidLocation) {
    return state.errorMessage
      ? `รอ GPS: ${state.errorMessage}`
      : 'กำลังขอพิกัดจากเบราว์เซอร์ — ยังไม่สแกนจนกว่าได้ GPS';
  }
  if (state.tracks.length === 0) {
    const link = state.wsConnected
      ? state.serverDetectActive
        ? 'ตรวจจับด้วย GPU เซิร์ฟเวอร์'
        : 'stream เชื่อมแล้ว'
      : 'stream กำลังเชื่อม...';
    return `โหมด stream (${link}) — เดินผ่านกล้องได้หลายคน`;
  }
  const names = state.tracks
    .map((t) => t.label)
    .filter((n): n is string => !!n)
    .slice(0, 3);
  const parts: string[] = [`พบ ${state.tracks.length} ใบหน้า`];
  if (names.length) {
    parts.push(names.join(', '));
  }
  if (state.checkingInCount > 0) {
    parts.push(stationModeBusyCountLabel(state.stationMode, state.checkingInCount));
  }
  if (state.queuePending > 0) {
    parts.push(`คิว GPU ${state.queuePending}`);
  }
  return parts.join(' · ');
}

/** Collapse ghost face tracks that overlap beyond `mergeIou`, keeping the richer/older track. */
export function mergeOverlappingFaceTracks(
  tracks: FaceTrack[],
  mergeIou: number,
  onDrop?: (track: FaceTrack) => void,
): FaceTrack[] {
  if (tracks.length <= 1) return tracks;
  const drop = new Set<number>();
  for (let i = 0; i < tracks.length; i++) {
    if (drop.has(tracks[i].id)) continue;
    for (let j = i + 1; j < tracks.length; j++) {
      if (drop.has(tracks[j].id)) continue;
      const a = tracks[i];
      const b = tracks[j];
      if (iou(a.targetBox, b.targetBox) < mergeIou && iou(a.box, b.box) < mergeIou) {
        continue;
      }
      const keepA =
        (a.memberId ? 1 : 0) !== (b.memberId ? 1 : 0)
          ? !!a.memberId
          : a.firstSeenAt <= b.firstSeenAt;
      const keep = keepA ? a : b;
      const lose = keepA ? b : a;
      if (!keep.memberId && lose.memberId) {
        keep.memberId = lose.memberId;
        keep.label = lose.label;
        keep.confidence = lose.confidence;
        keep.phase = lose.phase;
      } else if (!keep.label && lose.label) {
        keep.label = lose.label;
        keep.confidence = lose.confidence ?? keep.confidence;
      }
      onDrop?.(lose);
      drop.add(lose.id);
    }
  }
  return drop.size > 0 ? tracks.filter((t) => !drop.has(t.id)) : tracks;
}
