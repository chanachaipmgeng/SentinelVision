import { HttpClient } from '@angular/common/http';
import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, NgZone, OnDestroy, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, ParamMap, RouterModule } from '@angular/router';
import { environment } from '../../../../environments/environment';
import { CommonModule } from '@angular/common';
import { Subscription, combineLatest } from 'rxjs';
import { TokenService } from '../../../shared/services/token.service';
import { AuthService } from '../../../shared/services/auth.service';
import { AuthedImageService } from '../../../shared/services/authed-image.service';
import { SharedModule } from '../../../shared/shared.module';
import { CompanyLocationModel } from '../../models/company-location.model';
import { CompanyLocationService } from '../../services/company-location.service';
import {
  playCheckInBeep,
  playDuplicateBeep,
  playWarningBeep,
  unlockBeepAudio,
} from '../../../shared/utils/beep';
import { SystemSettingService } from '../../services/system-setting.service';
import {
  CompanyModuleConfigService,
  StationMode,
} from '../../services/company-module-config.service';
import {
  captureFaceCrop as captureFaceCropHelper,
  dataURLtoFile as dataURLtoFileHelper,
  describeCameraFailure,
  prepareDetectFrame,
  sampleDetectThumb as sampleDetectThumbHelper,
  scaleDetectionBoxes,
  startUserMedia,
} from './camera';
import type { CameraFailureKind } from './camera';
import {
  boxCenterDist,
  drawSmoothOverlay,
  iou,
  lerpBox,
  matchScore as matchScoreHelper,
  nmsBoxes as nmsBoxesHelper,
  SmoothBox,
} from './overlay';
import {
  resolveTtsSettings,
  speakCheckIn as speakCheckInHelper,
  TtsSettings,
  TtsTemplateKey,
  unlockSpeech,
} from './tts';
import {
  buildKioskCheckinExtras,
  buildKioskSession,
  buildKioskWsUrl,
  canSendKioskFrame,
  kioskWsSessionAction,
  WS_CONNECTING,
  WS_OPEN,
} from './ws';
import {
  frameChangeScore,
  KIOSK_STATIC_SCENE_DIFF,
  nextCaptureInterval,
} from './kiosk-tracker.service';
import {
  StationRouteContext,
  isAccessChrome,
  isAttendanceChrome,
  isEventChrome,
  isVisitorChrome,
  isWatchlistChrome,
  resolveStationRouteContext,
  shouldEnableDoorRelay,
  stationModeCaptureHint,
  stationModeRequiresGps,
  stationModeTitle,
} from '../scan-hub/scan-station-mode';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { FocusTrapDirective } from '../../../shared/directives/focus-trap.directive';
import { LocaleFormatService } from '../../../shared/services/locale-format.service';
import {
  KioskOfflineQueueService,
  OfflinePunchPayload,
} from './kiosk-offline-queue.service';

/** GPU pending depth at/above this enters degraded mode (slower detect + banner). */
const KIOSK_DEGRADED_QUEUE_PENDING = 8;

export type KioskPunchMode = 'AUTO' | 'CHECK_IN' | 'BREAK_OUT' | 'BREAK_IN' | 'CHECK_OUT';

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

type TrackPhase = 'watching' | 'capturing' | 'checking_in' | 'done' | 'cooldown';

interface FaceTrack {
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

@Component({
  selector: 'app-enroll-face',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule, RouterModule, TranslateModule, FocusTrapDirective],
  templateUrl: './enroll-face.component.html',
  styleUrl: './enroll-face.component.scss'
})
export class EnrollFaceComponent implements AfterViewInit, OnDestroy {
  @ViewChild('video') video!: ElementRef<HTMLVideoElement>;
  @ViewChild('canvas') canvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('clockTime') clockTimeEl?: ElementRef<HTMLElement>;
  @ViewChild('clockDate') clockDateEl?: ElementRef<HTMLElement>;
  @ViewChild('decorHour') decorHourEl?: ElementRef<HTMLElement>;
  @ViewChild('decorMinute') decorMinuteEl?: ElementRef<HTMLElement>;
  @ViewChild('decorSecond') decorSecondEl?: ElementRef<HTMLElement>;
  locationList: CompanyLocationModel[] = [];
  locationArea: CompanyLocationModel[] = [];
  companyId = '';
  /** Default 0,0 = invalid until browser geolocation succeeds. */
  location: { latitude: number; longitude: number } = { latitude: 0, longitude: 0 };
  locationReady = false;
  errorMessage: string | null = null;
  private geoWatchId: number | null = null;

  /** Camera open failed — recovery panel (steps + Retry + admin preview). */
  cameraFailed = false;
  cameraFailureKind: CameraFailureKind | null = null;
  cameraRecoveryTitle = '';
  cameraRecoverySteps: string[] = [];
  cameraRetrying = false;
  /** Admin/demo chrome without a live camera stream. */
  adminPreviewMode = false;

  /** Hybrid punch mode: AUTO (first scan = in, next = out) or explicit CHECK_IN / CHECK_OUT */
  punchMode: KioskPunchMode = 'AUTO';

  /**
   * Modular station mode from `/company/scan/:stationMode` (defaults ATTENDANCE on
   * `/company/timestamp-face` for backward-compatible attendance chrome).
   */
  stationMode: StationMode = 'ATTENDANCE';
  zoneId: string | null = null;
  eventId: string | null = null;
  totpOrPin = '';
  enableDoorRelayOnAttendance = false;
  zones: Array<{ zoneId: string; name: string; require2FA?: boolean }> = [];
  events: Array<{ eventId: string; name: string; capacity?: number; checkedInCount?: number }> = [];
  doorStatus: 'idle' | 'unlocked' | 'denied' = 'idle';
  welcomeBanner: string | null = null;
  seatNumber: string | null = null;
  vipArrivalName: string | null = null;

  /** D4 PDPA consent gate — blocks kiosk until current policy version is accepted. */
  consentRequired = false;
  consentLoading = false;
  consentPolicy: { version?: string; textTh?: string; textEn?: string } | null = null;
  private readonly consentStoragePrefix = 'dpu.pdpa.consent.';

  /** E6 kiosk large-text mode (html.dpu-kiosk-large-text). */
  largeTextMode = false;
  /** E8 degraded when GPU queue is backed up. */
  degradedMode = false;
  offlineQueuedCount = 0;
  reconcilingOffline = false;

  captureMessage = 'โหมด stream — WebSocket + คิว GPU ลงเวลาหลายคนแบบเรียลไทม์';
  activeFaceCount = 0;
  checkingInCount = 0;
  wsConnected = false;
  queuePending = 0;
  toastMessage = '';
  toastKind: 'success' | 'warning' | 'error' | 'info' = 'info';
  showToast = false;
  companyName = '';
  readonly clockTicks = Array.from({ length: 60 }, (_, i) => i);
  private ttsSettings: TtsSettings = resolveTtsSettings(null);

  feed: CheckInFeedItem[] = [];
  latestResult: CheckInFeedItem | null = null;

  attendance: KioskAttendance | null = null;
  homeLink = '/company/dashboard';

  private faceDetectionInterval: ReturnType<typeof setInterval> | null = null;
  private videoStream: MediaStream | null = null;
  private toastTimer: ReturnType<typeof setTimeout> | null = null;
  private clockTimer: ReturnType<typeof setInterval> | null = null;
  private attendanceTimer: ReturnType<typeof setInterval> | null = null;
  private detectBusy = false;
  private kioskWs: WebSocket | null = null;
  /** Server acknowledged `session` (`session_ok`); frames are refused by the server before this. */
  private wsSessionOk = false;
  private wsReconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private wsReqSeq = 0;
  private destroyWs = false;

  private tracks: FaceTrack[] = [];
  private nextTrackId = 1;
  private renderRafId: number | null = null;
  private canvasDirty = false;

  // Server-side detection only (WS `detect`) — local face-api was removed (E8).
  private wsDetectInFlight = false;
  private lastWsDetectAt = 0;
  private wsDetectMisses = 0;
  private serverDetectFailures = 0;
  private serverDetectPausedUntil = 0;
  private detectFrameCanvas: HTMLCanvasElement | null = null;
  private detectThumbCanvas: HTMLCanvasElement | null = null;
  private lastDetectThumb: Uint8ClampedArray | null = null;
  private lastDetectionsAt = 0;

  private readonly memberCooldownUntil = new Map<string, number>();
  private checkInInFlight = 0;
  private onlineHandler: (() => void) | null = null;
  private offlineHandler: (() => void) | null = null;
  /** SPA nav between `/company/scan/:stationMode` reuses this component — must not rely on snapshot alone. */
  private routeCtxSub?: Subscription;
  /** True when the active route carried `:stationMode` (false on legacy timestamp-face). */
  private routeHadStationMode = false;

  /**
   * 60fps easing toward latest detection.
   * Position and size use separate factors so zoom in/out feels snappy
   * while still smooth (lerp is applied around the box center).
   */
  private readonly boxPosLerp = 0.48;
  private readonly boxSizeLerp = 0.62;
  private readonly boxFastPosLerp = 0.78;
  private readonly boxFastSizeLerp = 0.85;
  private readonly boxFastCenterPx = 70;
  private readonly boxFastSizePx = 36;
  private readonly iouMatchMin = 0.12;
  /** Match by center distance as fraction of avg box diagonal (motion-tolerant). */
  private readonly centerMatchMax = 0.65;
  /**
   * Keep tracks across server-detect gaps (~110ms pace + GPU latency).
   * Too low → flicker; too high → stacked ghosts when walking.
   */
  private readonly trackMissTtlMs = 550;
  private readonly nmsIou = 0.35;
  private readonly trackMergeIou = 0.4;
  /** Short hold before walk-by check-in (face must stay briefly). */
  private readonly autoStartHoldMs = 150;
  private readonly memberCooldownMs = 5 * 60 * 1000;
  private readonly identifyEveryMs = 1200;
  /** Stream walk-by: single crop for lower latency (server still encodes once). */
  private readonly frameCount = 1;
  private readonly captureIntervalMs = 90;
  private readonly maxConcurrentCheckIn = 3;
  private readonly maxConcurrentIdentify = 2;
  private readonly minFaceWidth = 48;
  private readonly cropPad = 0.4;
  /** Backoff after a failed crop/check-in — keep short so walk-by can retry quickly. */
  private readonly retryFailMs = 900;
  /** Access denied (403, e.g. watchlist hit): back off longer so the kiosk does not hammer the alert path. */
  private readonly accessDeniedRetryMs = 10_000;
  /** Public-screen copy for a 403; never echo the server detail for denied faces. */
  private readonly accessDeniedMessage = 'ไม่สามารถลงเวลาได้ กรุณาติดต่อเจ้าหน้าที่';
  private readonly accessDeniedLabel = 'ไม่สามารถลงเวลาได้';
  private readonly checkInEndpoint = '/face/members/check-in-walkby';

  constructor(
    private http: HttpClient,
    private tokenService: TokenService,
    private authService: AuthService,
    private authedImages: AuthedImageService,
    private comLocationService: CompanyLocationService,
    private systemSettingService: SystemSettingService,
    private moduleConfig: CompanyModuleConfigService,
    private route: ActivatedRoute,
    private ngZone: NgZone,
    private cdr: ChangeDetectorRef,
    private offlineQueue: KioskOfflineQueueService,
    private localeFormat: LocaleFormatService,
    private translate: TranslateService,
  ) {
    const kiosk = this.tokenService.getKioskSession();
    const company = this.tokenService.getSelectCompany();
    // A paired kiosk is bound to its device record; the admin-selected company is only a fallback.
    this.companyId = kiosk?.companyId || company.companyId;
    this.companyName = company.companyName || kiosk?.deviceName || 'บริษัท';
    this.isKioskDevice = !!kiosk;
    this.homeLink = kiosk ? '/company/timestamp-face' : `/company/home/${this.companyId}`;
    // Initial paint before paramMap subscription; live updates go through onStationRouteParams.
    this.applyResolvedStationContext(
      resolveStationRouteContext(
        this.route.snapshot.paramMap.get('stationMode'),
        this.route.snapshot.queryParamMap.get('zoneId'),
        this.route.snapshot.queryParamMap.get('eventId'),
      ),
    );
    this.largeTextMode = sessionStorage.getItem('dpu.kiosk.largeText') === '1';
  }

  /** Apply pure route context onto component fields. */
  private applyResolvedStationContext(ctx: StationRouteContext): void {
    this.routeHadStationMode = ctx.routeHadMode;
    this.stationMode = ctx.stationMode;
    this.zoneId = ctx.zoneId;
    this.eventId = ctx.eventId;
    this.captureMessage = ctx.captureMessage;
  }

  /**
   * React to SPA navigation that reuses this component (same route config,
   * different `:stationMode` / query). Snapshot-only resolve stuck chrome on the
   * first visit — e.g. access-control → watchlist still showed Access Control.
   */
  private onStationRouteParams(params: ParamMap, query: ParamMap): void {
    const prevMode = this.stationMode;
    const prevZone = this.zoneId;
    const prevEvent = this.eventId;
    this.applyResolvedStationContext(
      resolveStationRouteContext(
        params.get('stationMode'),
        query.get('zoneId'),
        query.get('eventId'),
      ),
    );
    const modeChanged = prevMode !== this.stationMode;
    const idsChanged = prevZone !== this.zoneId || prevEvent !== this.eventId;
    if (!modeChanged && !idsChanged) {
      return;
    }
    if (modeChanged) {
      this.resetStationSessionForModeChange();
      this.loadZoneAndEventOptions();
      if (this.showAttendancePanel) {
        this.loadAttendance();
      }
    }
    this.sendWsSession();
    this.cdr.detectChanges();
  }

  /** Clear mode-specific chrome/session bits when switching scan station modes. */
  private resetStationSessionForModeChange(): void {
    this.doorStatus = 'idle';
    this.welcomeBanner = null;
    this.seatNumber = null;
    this.vipArrivalName = null;
    this.totpOrPin = '';
    this.feed = [];
    this.latestResult = null;
    this.attendance = null;
    this.punchMode = 'AUTO';
    this.memberCooldownUntil.clear();
    if (!(this.showAccessChrome || this.showVisitorChrome)) {
      this.zones = [];
    }
    if (!this.showEventChrome) {
      this.events = [];
    }
    for (const track of this.tracks) {
      if (track.captureTimer) {
        clearInterval(track.captureTimer);
        track.captureTimer = null;
      }
      track.phase = 'watching';
      track.label = null;
      track.memberId = null;
      track.confidence = null;
      track.captureFrames = [];
      track.statusText = null;
      track.identifyInFlight = false;
      track.firstSeenAt = Date.now();
    }
  }

  get kioskTitle(): string {
    return stationModeTitle(this.stationMode);
  }

  get showPunchChips(): boolean {
    return isAttendanceChrome(this.stationMode);
  }

  get showAccessChrome(): boolean {
    return isAccessChrome(this.stationMode);
  }

  get showWatchlistChrome(): boolean {
    return isWatchlistChrome(this.stationMode);
  }

  get showVisitorChrome(): boolean {
    return isVisitorChrome(this.stationMode);
  }

  get showEventChrome(): boolean {
    return isEventChrome(this.stationMode);
  }

  get showAttendancePanel(): boolean {
    return isAttendanceChrome(this.stationMode);
  }

  get doorRelayEnabled(): boolean {
    return shouldEnableDoorRelay(this.stationMode, this.enableDoorRelayOnAttendance);
  }

  get selectedZone(): { zoneId: string; name: string; require2FA?: boolean } | null {
    if (!this.zoneId) {
      return null;
    }
    return this.zones.find((z) => z.zoneId === this.zoneId) || null;
  }

  get selectedEvent(): {
    eventId: string;
    name: string;
    capacity?: number;
    checkedInCount?: number;
  } | null {
    if (!this.eventId) {
      return null;
    }
    return this.events.find((e) => e.eventId === this.eventId) || null;
  }

  get zoneRequires2FA(): boolean {
    return !!this.selectedZone?.require2FA;
  }

  onZoneChange(zoneId: string): void {
    this.zoneId = zoneId || null;
    this.sendWsSession();
  }

  onEventChange(eventId: string): void {
    this.eventId = eventId || null;
    this.sendWsSession();
  }

  emergencyUnlock(): void {
    if (!this.companyId || !this.zoneId) {
      this.notify('เลือกโซนประตูก่อนสั่งปลดล็อก', 'warning');
      return;
    }
    this.http
      .post(`/sentinel/company/${this.companyId}/zones/${this.zoneId}/trigger`, {
        reason: 'kiosk_emergency_unlock',
      })
      .subscribe({
        next: () => {
          this.doorStatus = 'unlocked';
          this.notify('สั่งปลดล็อกประตูฉุกเฉินแล้ว', 'info');
          this.cdr.detectChanges();
        },
        error: () => this.notify('สั่งปลดล็อกไม่สำเร็จ', 'error'),
      });
  }

  /** True when this tab holds a device-scoped kiosk session (paired via one-time code). */
  isKioskDevice = false;

  private imageSub?: { unsubscribe(): void };

  /** Forget the device session on this tablet (admin must issue a new pairing code). */
  unpairKiosk(): void {
    this.destroyWs = true;
    this.authService.logout(this.tokenService.getRefreshToken()).subscribe({
      next: () => this.tokenService.signOut(),
      error: () => this.tokenService.signOut(),
    });
  }

  setPunchMode(mode: KioskPunchMode): void {
    if (this.punchMode === mode) return;
    this.punchMode = mode;
    // Reset local cooldowns and active track phases so employees switching mode can scan right away
    this.memberCooldownUntil.clear();
    for (const t of this.tracks) {
      if (t.phase === 'done' || t.phase === 'cooldown') {
        t.phase = 'watching';
        t.firstSeenAt = Date.now();
      }
    }
    const modeLabel =
      mode === 'CHECK_IN'
        ? 'โหมดเข้างาน (Check-In)'
        : mode === 'BREAK_OUT'
          ? 'โหมดพักนอก (Break-Out)'
          : mode === 'BREAK_IN'
            ? 'โหมดพักเข้า (Break-In)'
            : mode === 'CHECK_OUT'
              ? 'โหมดออกงาน (Check-Out)'
              : 'โหมดอัตโนมัติ (Hybrid: เข้า → พักนอก → พักเข้า → ออก)';
    this.notify(`สลับเป็น ${modeLabel}`, 'info');
  }

  get checkedInCount(): number {
    return this.attendance?.summary?.checkedInCount ?? 0;
  }

  get rosterList(): KioskRosterPerson[] {
    return this.attendance?.checkedIn || [];
  }

  get inArea(): boolean {
    return this.locationReady && this.locationArea.length > 0;
  }

  get areaLabel(): string {
    if (!this.gpsRequired) {
      return 'ไม่ใช้ GPS';
    }
    if (!this.locationReady) {
      return this.errorMessage ? 'ไม่มี GPS' : 'รอพิกัด…';
    }
    if (this.inArea) {
      return this.locationArea[0].locationName || 'ในพื้นที่';
    }
    return 'นอกพื้นที่';
  }

  /** Attendance / hybrid still need a geofence fix; other station modes do not. */
  get gpsRequired(): boolean {
    return stationModeRequiresGps(this.stationMode);
  }

  /** Loud GPS banner only when the active mode actually needs a fix. */
  get showGpsError(): boolean {
    return this.gpsRequired && !!this.errorMessage;
  }

  /** HUD / punch chips wait on GPS only for geofenced modes. */
  get waitingOnGps(): boolean {
    return this.gpsRequired && !this.locationReady;
  }

  /** True when browser returned a real fix (not the 0,0 placeholder). */
  get hasValidLocation(): boolean {
    const lat = Number(this.location?.latitude);
    const lng = Number(this.location?.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      return false;
    }
    // Null Island / uninitialized defaults used by this kiosk
    return Math.abs(lat) > 0.0001 || Math.abs(lng) > 0.0001;
  }

  get successCount(): number {
    return this.feed.filter((f) => f.statusKind === 'success').length;
  }

  get warningCount(): number {
    return this.feed.filter((f) => f.statusKind === 'warning').length;
  }

  get errorCount(): number {
    return this.feed.filter((f) => f.statusKind === 'error').length;
  }

  get sessionTotal(): number {
    return this.feed.filter((f) => f.statusKind !== 'error').length;
  }

  ngOnInit() {
    document.documentElement.classList.add('dpu-kiosk-mode');
    this.applyLargeTextClass();
    this.imageSub = this.authedImages.loaded$.subscribe(() => this.cdr.detectChanges());
    // Keep chrome/mode in sync when Angular reuses this component across scan routes.
    this.routeCtxSub = combineLatest([this.route.paramMap, this.route.queryParamMap]).subscribe(
      ([params, query]) => this.onStationRouteParams(params, query),
    );
    this.getCurrentLocation();
    unlockBeepAudio();
    unlockSpeech();
    this.loadTtsSettings();
    this.loadModuleStationDefaults();
    this.loadZoneAndEventOptions();
    this.loadConsentPolicy();
    this.refreshOfflineQueueCount();
    this.bindOnlineListeners();
    this.startVideo();
    this.getCompanyLocation();
    this.ngZone.runOutsideAngular(() => this.connectKioskWs());
    if (this.showAttendancePanel) {
      this.loadAttendance();
    }
    this.ngZone.runOutsideAngular(() => {
      this.attendanceTimer = setInterval(() => {
        if (this.showAttendancePanel) {
          this.loadAttendance();
        }
        this.loadTtsSettings();
      }, 15000);
    });
  }

  toggleLargeText(): void {
    this.largeTextMode = !this.largeTextMode;
    sessionStorage.setItem('dpu.kiosk.largeText', this.largeTextMode ? '1' : '0');
    this.applyLargeTextClass();
  }

  private applyLargeTextClass(): void {
    document.documentElement.classList.toggle('dpu-kiosk-large-text', this.largeTextMode);
  }

  private bindOnlineListeners(): void {
    this.onlineHandler = () => {
      this.ngZone.run(() => {
        void this.reconcileOfflineQueue();
      });
    };
    this.offlineHandler = () => {
      this.ngZone.run(() => this.cdr.detectChanges());
    };
    window.addEventListener('online', this.onlineHandler);
    window.addEventListener('offline', this.offlineHandler);
    if (typeof navigator !== 'undefined' && navigator.onLine) {
      void this.reconcileOfflineQueue();
    }
  }

  private async refreshOfflineQueueCount(): Promise<void> {
    try {
      this.offlineQueuedCount = await this.offlineQueue.count();
      this.cdr.detectChanges();
    } catch {
      this.offlineQueuedCount = 0;
    }
  }

  private async enqueueOfflinePunch(payload: {
    images: string[];
    latitude: number;
    longitude: number;
    punchType: string;
    note: string;
    zoneId?: string | null;
    eventId?: string | null;
    enableDoorRelay?: boolean;
    totpOrPin?: string | null;
  }): Promise<void> {
    try {
      await this.offlineQueue.enqueue({
        companyId: this.companyId,
        images: payload.images,
        latitude: payload.latitude,
        longitude: payload.longitude,
        punchType: payload.punchType,
        stationMode: this.stationMode,
        zoneId: payload.zoneId,
        eventId: payload.eventId,
        enableDoorRelay: payload.enableDoorRelay,
        totpOrPin: payload.totpOrPin,
        note: payload.note,
      });
      await this.refreshOfflineQueueCount();
      this.notify(this.translate.instant('Queued while offline'), 'warning');
    } catch {
      this.notify('ไม่สามารถบันทึกคิวนอกสายได้', 'error');
    }
  }

  /** Flush IndexedDB punches when connectivity returns. */
  async reconcileOfflineQueue(): Promise<void> {
    if (this.reconcilingOffline || (typeof navigator !== 'undefined' && !navigator.onLine)) {
      return;
    }
    let rows: OfflinePunchPayload[] = [];
    try {
      rows = await this.offlineQueue.list();
    } catch {
      return;
    }
    if (!rows.length) {
      this.offlineQueuedCount = 0;
      return;
    }
    this.reconcilingOffline = true;
    this.cdr.detectChanges();
    for (const row of rows) {
      try {
        const formData = new FormData();
        row.images.forEach((dataUrl, index) => {
          formData.append('files', this.dataURLtoFile(dataUrl, `offline_${row.id}_${index}.jpg`));
        });
        formData.append('companyId', row.companyId);
        formData.append('latitude', String(row.latitude));
        formData.append('longitude', String(row.longitude));
        formData.append('note', row.note || 'Face kiosk offline reconcile');
        formData.append('punchType', row.punchType);
        formData.append('stationMode', row.stationMode);
        if (row.zoneId) {
          formData.append('zoneId', row.zoneId);
        }
        if (row.eventId) {
          formData.append('eventId', row.eventId);
        }
        if (row.enableDoorRelay) {
          formData.append('enableDoorRelay', 'true');
        }
        if (row.totpOrPin) {
          formData.append('totpOrPin', row.totpOrPin);
        }
        await new Promise<void>((resolve, reject) => {
          this.http.post(environment.baseUrl + this.checkInEndpoint, formData).subscribe({
            next: () => resolve(),
            error: (err) => reject(err),
          });
        });
        await this.offlineQueue.remove(row.id);
      } catch (err: unknown) {
        const status = (err as { status?: number })?.status;
        await this.offlineQueue.markAttempt(row.id, `status=${status ?? 'network'}`);
        if (this.offlineQueue.isLikelyOffline(err as { status?: number })) {
          break;
        }
      }
    }
    this.reconcilingOffline = false;
    await this.refreshOfflineQueueCount();
  }

  private updateDegradedMode(): void {
    const next = this.queuePending >= KIOSK_DEGRADED_QUEUE_PENDING;
    if (next !== this.degradedMode) {
      this.degradedMode = next;
      this.cdr.detectChanges();
    }
  }

  private consentStorageKey(): string {
    return `${this.consentStoragePrefix}${this.companyId}`;
  }

  private loadConsentPolicy(): void {
    if (!this.companyId) {
      return;
    }
    this.consentLoading = true;
    this.http.get<any>(`/hr/company/${this.companyId}/pdpa/consent-policy`).subscribe({
      next: (policy) => {
        this.consentPolicy = policy || null;
        const accepted = sessionStorage.getItem(this.consentStorageKey());
        this.consentRequired = !accepted || accepted !== (policy?.version || '1.0');
        this.consentLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.consentLoading = false;
        this.consentRequired = false;
      },
    });
  }

  acceptConsentPolicy(): void {
    if (!this.companyId || !this.consentPolicy) {
      this.consentRequired = false;
      return;
    }
    const version = this.consentPolicy.version || '1.0';
    sessionStorage.setItem(this.consentStorageKey(), version);
    this.consentRequired = false;
    this.cdr.detectChanges();
  }

  consentText(): string {
    const lang = (
      this.translate.currentLang ||
      sessionStorage.getItem('Lang') ||
      'th'
    ).toLowerCase();
    if (lang.startsWith('en')) {
      return this.consentPolicy?.textEn || this.consentPolicy?.textTh || '';
    }
    return this.consentPolicy?.textTh || this.consentPolicy?.textEn || '';
  }

  /** Apply company defaultStationMode / zone / door-relay when route omitted them. */
  private loadModuleStationDefaults(): void {
    if (!this.companyId) {
      return;
    }
    this.moduleConfig.getModuleConfig(this.companyId).subscribe({
      next: (cfg) => {
        this.enableDoorRelayOnAttendance = !!cfg.scanActionRules?.enableDoorRelayOnAttendance;
        // `/company/timestamp-face` has no :stationMode — keep ATTENDANCE chrome, but honor
        // UNIFIED_HYBRID / door-relay defaults from module-config when set as company default.
        // Use the live routeHadStationMode flag (paramMap-driven), not snapshot alone.
        if (!this.routeHadStationMode && cfg.defaultStationMode === 'UNIFIED_HYBRID') {
          this.stationMode = 'UNIFIED_HYBRID';
          this.captureMessage = stationModeCaptureHint(this.stationMode);
        }
        if (!this.zoneId && cfg.defaultZoneId) {
          this.zoneId = cfg.defaultZoneId;
        }
        if (!this.eventId && cfg.defaultEventId) {
          this.eventId = cfg.defaultEventId;
        }
        this.sendWsSession();
        this.cdr.detectChanges();
      },
    });
  }

  private loadZoneAndEventOptions(): void {
    if (!this.companyId) {
      return;
    }
    if (this.showAccessChrome || this.showVisitorChrome) {
      this.http.get<any[]>(`/sentinel/company/${this.companyId}/zones`).subscribe({
        next: (rows) => {
          this.zones = rows || [];
          if (!this.zoneId && this.zones.length === 1) {
            this.zoneId = this.zones[0].zoneId;
          }
          this.cdr.detectChanges();
        },
        error: () => (this.zones = []),
      });
    }
    if (this.showEventChrome) {
      this.http.get<any[]>(`/sentinel/company/${this.companyId}/events`).subscribe({
        next: (rows) => {
          this.events = rows || [];
          if (!this.eventId && this.events.length === 1) {
            this.eventId = this.events[0].eventId;
          }
          this.cdr.detectChanges();
        },
        error: () => (this.events = []),
      });
    }
  }

  ngAfterViewInit(): void {
    this.startSceneClock();
  }

  /** Decorative + header clock only — never trigger component CD (face/WS work). */
  private startSceneClock(): void {
    this.tickSceneClock();
    this.ngZone.runOutsideAngular(() => {
      this.clockTimer = setInterval(() => this.tickSceneClock(), 1000);
    });
  }

  private tickSceneClock(): void {
    const now = new Date();
    const hh = now.getHours();
    const mm = now.getMinutes();
    const ss = now.getSeconds();
    const pad = (n: number) => String(n).padStart(2, '0');
    const timeEl = this.clockTimeEl?.nativeElement;
    const dateEl = this.clockDateEl?.nativeElement;
    if (timeEl) {
      timeEl.textContent = `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
    }
    if (dateEl) {
      dateEl.textContent = this.localeFormat.formatDate(now, {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
    }

    const hourDeg = (hh % 12) * 30 + mm * 0.5;
    const minuteDeg = mm * 6 + ss * 0.1;
    const secondDeg = ss * 6;
    const hourHand = this.decorHourEl?.nativeElement;
    const minuteHand = this.decorMinuteEl?.nativeElement;
    const secondHand = this.decorSecondEl?.nativeElement;
    if (hourHand) hourHand.style.transform = `rotate(${hourDeg}deg)`;
    if (minuteHand) minuteHand.style.transform = `rotate(${minuteDeg}deg)`;
    if (secondHand) secondHand.style.transform = `rotate(${secondDeg}deg)`;
  }

  private loadTtsSettings(): void {
    this.systemSettingService.getTtsSettings().subscribe({
      next: (settings) => {
        this.ttsSettings = settings;
      },
      error: () => {
        /* keep defaults / last known */
      },
    });
  }

  private speakCheckIn(
    key: TtsTemplateKey,
    vars: { name?: string; firstName?: string; employeeId?: string },
  ): void {
    // Use cached settings (loaded on init + refreshed with attendance poll).
    speakCheckInHelper(this.ttsSettings, key, vars);
  }

  ngOnDestroy() {
    document.documentElement.classList.remove('dpu-kiosk-mode');
    document.documentElement.classList.remove('dpu-kiosk-large-text');
    if (this.onlineHandler) {
      window.removeEventListener('online', this.onlineHandler);
    }
    if (this.offlineHandler) {
      window.removeEventListener('offline', this.offlineHandler);
    }
    this.destroyWs = true;
    this.routeCtxSub?.unsubscribe();
    this.imageSub?.unsubscribe();
    if (this.geoWatchId != null && navigator.geolocation) {
      navigator.geolocation.clearWatch(this.geoWatchId);
      this.geoWatchId = null;
    }
    if (this.faceDetectionInterval) {
      clearInterval(this.faceDetectionInterval);
    }
    if (this.renderRafId != null) {
      cancelAnimationFrame(this.renderRafId);
      this.renderRafId = null;
    }
    if (this.toastTimer) {
      clearTimeout(this.toastTimer);
    }
    if (this.clockTimer) {
      clearInterval(this.clockTimer);
    }
    if (this.attendanceTimer) {
      clearInterval(this.attendanceTimer);
    }
    if (this.wsReconnectTimer) {
      clearTimeout(this.wsReconnectTimer);
    }
    for (const track of this.tracks) {
      if (track.captureTimer) {
        clearInterval(track.captureTimer);
      }
    }
    if (this.kioskWs) {
      try {
        this.kioskWs.close();
      } catch {
        /* ignore */
      }
      this.kioskWs = null;
    }
    if (this.videoStream) {
      this.videoStream.getTracks().forEach((track) => track.stop());
    }
  }

  getCompanyLocation() {
    this.comLocationService.getLists(this.companyId).subscribe((result) => {
      this.locationList = result;
      this.getCurrentLocation();
    });
  }

  startVideo(): void {
    if (this.videoStream) {
      this.videoStream.getTracks().forEach((track) => track.stop());
      this.videoStream = null;
    }
    if (this.video?.nativeElement) {
      this.video.nativeElement.srcObject = null;
    }
    this.cameraRetrying = true;
    this.cdr.detectChanges();
    startUserMedia({ video: { facingMode: 'user' } }).then((result) => {
      this.ngZone.run(() => {
        this.cameraRetrying = false;
        if (!result.ok) {
          console.error('Error accessing camera: ', result.error);
          const info = describeCameraFailure(result.error);
          this.cameraFailed = true;
          this.adminPreviewMode = false;
          this.cameraFailureKind = info.kind;
          this.cameraRecoveryTitle = info.title;
          this.cameraRecoverySteps = info.steps;
          this.captureMessage = info.title;
          this.notify(info.title, 'warning');
          this.cdr.detectChanges();
          return;
        }
        this.cameraFailed = false;
        this.adminPreviewMode = false;
        this.cameraFailureKind = null;
        this.cameraRecoveryTitle = '';
        this.cameraRecoverySteps = [];
        this.videoStream = result.stream;
        this.video.nativeElement.srcObject = result.stream;
        unlockBeepAudio();
        unlockSpeech();
        this.cdr.detectChanges();
      });
    });
  }

  /** Re-request getUserMedia after the operator fixes permission / device. */
  retryCamera(): void {
    this.adminPreviewMode = false;
    this.startVideo();
  }

  /** Inspect kiosk chrome without a camera (admin / headless / demo). */
  enterAdminPreview(): void {
    this.adminPreviewMode = true;
    this.captureMessage = 'Admin preview — ตรวจ chrome โดยไม่ใช้กล้อง (ไม่มี stream)';
    this.notify('เข้าสู่ Admin preview (ไม่ใช้กล้อง)', 'info');
    this.cdr.detectChanges();
  }

  /** Re-request browser geolocation when GPS is required for this station. */
  retryGps(): void {
    if (!this.gpsRequired) {
      return;
    }
    this.errorMessage = null;
    this.getCurrentLocation();
  }

  async detectFace() {
    const videoEl = this.video.nativeElement as HTMLVideoElement;
    const displaySize = { width: videoEl.width, height: videoEl.height };

    if (this.faceDetectionInterval) {
      clearInterval(this.faceDetectionInterval);
    }

    this.ngZone.runOutsideAngular(() => {
      this.faceDetectionInterval = setInterval(async () => {
        if (!videoEl.srcObject || videoEl.readyState < 2) {
          return;
        }
        const nowMs = Date.now();

        // Detection stalled (WS dead / server slow) — expire boxes instead of freezing them.
        if (this.tracks.length > 0 && this.lastDetectionsAt > 0 && nowMs - this.lastDetectionsAt > 1600) {
          this.updateTracks([], nowMs);
        }

        // Prefer server-side detection (InsightFace GPU) once the session is acknowledged.
        // Block frames while the PDPA consent overlay is showing (D4).
        if (
          !this.consentRequired &&
          this.wsConnected &&
          this.wsSessionOk &&
          nowMs >= this.serverDetectPausedUntil
        ) {
          this.sendDetectFrame(videoEl);
          return;
        }
        if (this.tracks.length > 0 && this.lastDetectionsAt > 0 && nowMs - this.lastDetectionsAt > 1600) {
          this.updateTracks([], nowMs);
        }
      }, 140);

      this.startRenderLoop(displaySize);
    });
  }

  /** Shared post-detection pipeline: tracks, identify slots, check-in, HUD status. */
  private processDetections(boxes: SmoothBox[], now: number): void {
    // Empty frame between GPU detects: keep last boxes (avoids blink) until miss TTL.
    if (boxes.length === 0 && this.tracks.length > 0) {
      return;
    }
    this.lastDetectionsAt = now;
    this.updateTracks(boxes, now);

    let identifySlots = this.maxConcurrentIdentify - this.tracks.filter((t) => t.identifyInFlight).length;
    for (const track of this.tracks) {
      if (identifySlots <= 0) {
        break;
      }
      if (this.shouldIdentify(track, now)) {
        identifySlots -= 1;
        this.runTrackIdentify(track);
      }
    }

    for (const track of this.tracks) {
      if (this.shouldStartCheckIn(track, now)) {
        this.startTrackCapture(track);
      }
    }

    this.activeFaceCount = this.tracks.length;
    this.checkingInCount = this.tracks.filter(
      (t) => t.phase === 'capturing' || t.phase === 'checking_in',
    ).length;
    const status = this.buildStatusMessage();
    if (status !== this.captureMessage) {
      this.ngZone.run(() => {
        this.captureMessage = status;
        this.cdr.detectChanges();
      });
    }
  }

  /** Send one downscaled frame for server-side detection (paced, one in flight). */
  private sendDetectFrame(videoEl: HTMLVideoElement): void {
    const now = Date.now();
    if (this.wsDetectInFlight) {
      if (now - this.lastWsDetectAt < 1500) {
        return; // wait for response
      }
      // Response never arrived — count a miss; repeated misses = rest + reconnect.
      this.wsDetectInFlight = false;
      this.wsDetectMisses += 1;
      if (this.wsDetectMisses >= 2) {
        this.wsDetectMisses = 0;
        this.serverDetectPausedUntil = now + 15000;
        try {
          this.kioskWs?.close();
        } catch {
          /* onclose triggers reconnect */
        }
        return;
      }
    }

    const prepared = prepareDetectFrame(videoEl, this.detectFrameCanvas);
    if (!prepared) {
      return;
    }
    this.detectFrameCanvas = prepared.canvas;
    const canvas = prepared.canvas;

    // Thumbnail diff before JPEG encode — skip send when the scene is static.
    const sampled = sampleDetectThumbHelper(canvas, this.detectThumbCanvas);
    this.detectThumbCanvas = sampled.canvas;
    const thumb = sampled.pixels;
    const changeScore = frameChangeScore(this.lastDetectThumb, thumb);
    const staticScene =
      this.lastDetectThumb != null && changeScore < KIOSK_STATIC_SCENE_DIFF;

    const hasTracks = this.tracks.length > 0;
    const allSettled =
      hasTracks &&
      this.tracks.every((t) => t.phase === 'done' || t.phase === 'cooldown');
    const trackingLocked =
      hasTracks &&
      this.tracks.every(
        (t) =>
          !!t.memberId ||
          t.phase === 'capturing' ||
          t.phase === 'checking_in' ||
          t.phase === 'done' ||
          t.phase === 'cooldown',
      );
    const idleNoFaces =
      this.tracks.length === 0 &&
      (this.lastDetectionsAt === 0 || now - this.lastDetectionsAt > 2000);

    const minGap = nextCaptureInterval(this.queuePending, {
      idleNoFaces,
      staticScene,
      trackingLocked,
      allSettled,
      hasTracks,
    });
    if (now - this.lastWsDetectAt < minGap) {
      return;
    }

    const dataUrl = canvas.toDataURL('image/jpeg', 0.7);

    if (this.wsSend({ type: 'detect', requestId: `d-${now}`, image: dataUrl })) {
      this.wsDetectInFlight = true;
      this.lastWsDetectAt = now;
      // Refresh baseline after a successful send so motion is relative to last sent frame.
      this.lastDetectThumb = thumb;
      return;
    }

    // Send failed — the connected flag is stale (socket died without onclose).
    // Resync so the local fallback takes over next tick, and force a reconnect.
    if (!this.kioskWs || this.kioskWs.readyState !== WS_OPEN) {
      this.ngZone.run(() => {
        this.wsConnected = false;
        this.cdr.detectChanges();
      });
      this.connectKioskWs();
    }
  }

  /** Server detection result → display-space boxes → shared pipeline. */
  private onServerDetected(msg: any): void {
    this.wsDetectInFlight = false;
    this.wsDetectMisses = 0;
    this.serverDetectFailures = 0;
    if (msg?.queue?.pending != null) {
      this.queuePending = Number(msg.queue.pending) || 0;
      this.updateDegradedMode();
    }

    const videoEl = this.video?.nativeElement;
    if (!videoEl) {
      return;
    }
    const frameW = Number(msg.frameWidth) || 1;
    const frameH = Number(msg.frameHeight) || 1;
    const displayW = videoEl.width || 640;
    const displayH = videoEl.height || 480;
    const boxes = scaleDetectionBoxes(
      Array.isArray(msg.faces) ? msg.faces : [],
      frameW,
      frameH,
      displayW,
      displayH,
    );
    this.processDetections(boxes, Date.now());
  }

  private onServerDetectError(): void {
    this.wsDetectInFlight = false;
    this.serverDetectFailures += 1;
    if (this.serverDetectFailures >= 3) {
      // Pause server detect briefly; do not fall back to local models (removed in E8).
      this.serverDetectPausedUntil = Date.now() + 30000;
      this.serverDetectFailures = 0;
      this.degradedMode = true;
      this.cdr.detectChanges();
    }
  }

  /** 60fps canvas loop (outside Angular): ease boxes toward latest detection and draw. */
  private startRenderLoop(displaySize: { width: number; height: number }): void {
    if (this.renderRafId != null) {
      cancelAnimationFrame(this.renderRafId);
    }
    const step = () => {
      if (this.tracks.length > 0) {
        for (const track of this.tracks) {
          const jump = boxCenterDist(track.box, track.targetBox);
          const sizeDelta =
            Math.abs(track.box.width - track.targetBox.width) +
            Math.abs(track.box.height - track.targetBox.height);
          const posT = jump > this.boxFastCenterPx ? this.boxFastPosLerp : this.boxPosLerp;
          const sizeT = sizeDelta > this.boxFastSizePx ? this.boxFastSizeLerp : this.boxSizeLerp;
          track.box = lerpBox(track.box, track.targetBox, posT, sizeT);
        }
        this.drawAllTracks(displaySize);
        this.canvasDirty = true;
      } else if (this.canvasDirty) {
        const ctx = this.canvas.nativeElement.getContext('2d') as CanvasRenderingContext2D;
        ctx.clearRect(0, 0, displaySize.width, displaySize.height);
        this.canvasDirty = false;
      }
      this.renderRafId = requestAnimationFrame(step);
    };
    this.renderRafId = requestAnimationFrame(step);
  }

  private buildStatusMessage(): string {
    if (this.adminPreviewMode) {
      return 'Admin preview — ไม่มีกล้อง; ตรวจ layout / status pills ได้';
    }
    if (this.cameraFailed) {
      return this.cameraRecoveryTitle || 'ไม่สามารถเปิดกล้องได้ — ดูขั้นตอนด้านล่าง';
    }
    if (this.gpsRequired && !this.hasValidLocation) {
      return this.errorMessage
        ? `รอ GPS: ${this.errorMessage}`
        : 'กำลังขอพิกัดจากเบราว์เซอร์ — ยังไม่ลงเวลาจนกว่าได้ GPS';
    }
    if (this.tracks.length === 0) {
      const serverDetect = this.wsConnected && Date.now() >= this.serverDetectPausedUntil;
      const link = this.wsConnected
        ? serverDetect
          ? 'ตรวจจับด้วย GPU เซิร์ฟเวอร์'
          : 'stream เชื่อมแล้ว'
        : 'stream กำลังเชื่อม...';
      return `โหมด stream (${link}) — เดินผ่านกล้องได้หลายคน`;
    }
    const names = this.tracks
      .map((t) => t.label)
      .filter((n): n is string => !!n)
      .slice(0, 3);
    const busy = this.checkingInCount;
    const parts: string[] = [`พบ ${this.tracks.length} ใบหน้า`];
    if (names.length) {
      parts.push(names.join(', '));
    }
    if (busy > 0) {
      parts.push(`กำลังลงเวลา ${busy} คน`);
    }
    if (this.queuePending > 0) {
      parts.push(`คิว GPU ${this.queuePending}`);
    }
    return parts.join(' · ');
  }

  private kioskWsUrl(): string {
    return buildKioskWsUrl(environment.baseUrl || '');
  }

  private connectKioskWs() {
    if (this.destroyWs) {
      return;
    }
    if (
      this.kioskWs &&
      (this.kioskWs.readyState === WS_OPEN ||
        this.kioskWs.readyState === WS_CONNECTING)
    ) {
      return;
    }

    try {
      const ws = new WebSocket(this.kioskWsUrl());
      this.kioskWs = ws;

      ws.onopen = () => {
        this.wsSessionOk = false;
        this.ngZone.run(() => {
          this.wsConnected = true;
          this.cdr.detectChanges();
        });
        // Server requires `session` first; detect/identify/checkin wait for `session_ok`.
        this.sendWsSession();
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg?.type === 'detected') {
            // High-frequency detection frames: handle outside Angular
            this.onServerDetected(msg);
            return;
          }
          if (msg?.type === 'error' && msg?.intent === 'detect') {
            this.onServerDetectError();
            return;
          }
          this.ngZone.run(() => this.onKioskWsMessage(msg));
        } catch (e) {
          console.error('WS parse error', e);
        }
      };

      ws.onclose = () => {
        this.wsDetectInFlight = false;
        this.wsSessionOk = false;
        this.ngZone.run(() => {
          this.wsConnected = false;
          this.cdr.detectChanges();
        });
        this.kioskWs = null;
        if (!this.destroyWs) {
          this.wsReconnectTimer = setTimeout(() => this.connectKioskWs(), 2000);
        }
      };

      ws.onerror = () => {
        // onclose will reconnect
      };
    } catch (e) {
      console.error('WS connect failed', e);
      if (!this.destroyWs) {
        this.wsReconnectTimer = setTimeout(() => this.connectKioskWs(), 3000);
      }
    }
  }

  private wsSend(payload: Record<string, unknown>): boolean {
    // Only `session` may go out before the server acknowledges it (otherwise it closes with 1008).
    if (!this.kioskWs || !canSendKioskFrame(payload['type'], this.wsSessionOk, this.kioskWs.readyState)) {
      return false;
    }
    this.kioskWs.send(JSON.stringify(payload));
    return true;
  }

  private nextWsRequestId(trackId: number): string {
    this.wsReqSeq += 1;
    return `${trackId}-${Date.now()}-${this.wsReqSeq}`;
  }

  private refreshKioskToken(): void {
    const refresh = this.tokenService.getRefreshToken();
    if (!refresh) {
      return;
    }
    // Rotation: the refresh token we hold is single-use; the server returns a new pair.
    this.authService
      .refreshSession(refresh.replace('Bearer ', ''), this.tokenService.isKioskSession())
      .subscribe({
        next: (tokens) => {
          if (tokens.accessToken) {
            this.tokenService.saveToken(tokens.accessToken);
          }
          if (tokens.refreshToken) {
            this.tokenService.saveRefreshToken(tokens.refreshToken);
          }
          this.sendWsSession();
        },
        error: () => {
          // Revoked / reused refresh token: the device must be paired again.
          this.notify('เซสชันอุปกรณ์หมดอายุ กรุณาจับคู่ตู้ Kiosk ใหม่', 'error');
          this.destroyWs = true;
          this.tokenService.signOut();
        },
      });
  }

  private onKioskWsMessage(msg: {
    type?: string;
    queue?: { pending?: number };
    trackId?: number | string;
    memberId?: string;
    member?: { memberId?: string; fullName?: string; firstName?: string };
    employee?: { fullName?: string };
    confidencePercent?: number;
    dedupeSeconds?: number;
    duplicate?: boolean;
    intent?: string;
    status?: number;
    detail?: string;
    [key: string]: unknown;
  }) {
    if (msg?.queue?.pending != null) {
      this.queuePending = Number(msg.queue.pending) || 0;
      this.updateDegradedMode();
    }

    switch (kioskWsSessionAction(msg)) {
      case 'session_ok':
        this.wsSessionOk = true;
        this.cdr.detectChanges();
        return;
      case 'refresh_token':
        this.refreshKioskToken();
        return;
      case 'invalid_session':
        // Server closes the socket after this; refresh the token so the reconnect's `session` is valid.
        this.wsSessionOk = false;
        this.refreshKioskToken();
        return;
      case 'none':
        break;
    }

    if (msg.type === 'identified') {
      const trackId = Number(msg.trackId);
      const t = this.tracks.find((x) => x.id === trackId);
      if (!t) {
        return;
      }
      t.identifyInFlight = false;
      t.memberId = msg.memberId || msg.member?.memberId || null;
      t.label = msg.member?.fullName || msg.member?.firstName || t.label;
      const confidence = Number(msg.confidencePercent ?? NaN);
      t.confidence = Number.isFinite(confidence) ? confidence : null;
      if (t.memberId && this.isMemberOnCooldown(t.memberId)) {
        t.phase = 'cooldown';
      }
      this.cdr.detectChanges();
      return;
    }

    if (msg.type === 'checked_in') {
      this.checkInInFlight = Math.max(0, this.checkInInFlight - 1);
      const trackId = Number(msg.trackId);
      const t = this.tracks.find((x) => x.id === trackId);
      const memberId = msg.memberId || msg.member?.memberId || t?.memberId;
      if (memberId) {
        const dedupeMs = msg.dedupeSeconds
          ? Number(msg.dedupeSeconds) * 1000
          : this.memberCooldownMs;
        this.setMemberCooldown(memberId, dedupeMs);
      }

      if (t) {
        t.phase = 'cooldown';
        t.memberId = memberId || t.memberId;
        t.label = msg.employee?.fullName || msg.member?.fullName || t.label;
      }

      this.handleCheckInSuccess(msg, [], t, !!msg.duplicate);
      return;
    }

    if (msg.type === 'error') {
      const trackId = Number(msg.trackId);
      const t = trackId ? this.tracks.find((x) => x.id === trackId) : null;
      if (msg.intent === 'identify' && t) {
        t.identifyInFlight = false;
      }
      if (msg.intent === 'checkin') {
        this.checkInInFlight = Math.max(0, this.checkInInFlight - 1);
        if (t) {
          t.phase = 'watching';
          t.retryAfter = Date.now() + this.retryFailMs;
          t.captureFrames = [];
        }
      }
      if (Number(msg.status) === 403) {
        this.applyAccessDenied(t ?? undefined, msg.intent === 'checkin');
      } else if (msg.intent === 'checkin' && msg.detail) {
        this.notify(`ข้ามใบหน้าหนึ่งรายการ: ${msg.detail}`, 'warning');
      }
      this.cdr.detectChanges();
    }
  }

  /**
   * Generic denied state for a 403 from identify / check-in (e.g. a watchlist hit).
   * The server already withholds identity; the kiosk must not echo any detail,
   * keep a stale label, or retry immediately.
   */
  private applyAccessDenied(track: FaceTrack | undefined, showToast: boolean) {
    if (track) {
      track.memberId = null;
      track.confidence = null;
      track.label = this.accessDeniedLabel;
      track.identifyInFlight = false;
      track.lastIdentifyAt = Date.now() + this.accessDeniedRetryMs;
      if (track.phase === 'capturing') {
        track.phase = 'watching';
        track.captureFrames = [];
      }
      track.retryAfter = Date.now() + this.accessDeniedRetryMs;
    }
    if (this.showAccessChrome || this.doorRelayEnabled) {
      this.doorStatus = 'denied';
    }
    if (showToast) {
      this.notify(this.accessDeniedMessage, 'error');
    }
  }

  /** Apply modular scan payload fields (door / VIP / event seat) onto kiosk HUD state. */
  private applyStationModeResult(response: any): void {
    if (!response) {
      return;
    }
    if (response.accessGranted === true || response.decision === 'ACCESS_GRANTED') {
      this.doorStatus = 'unlocked';
    } else if (response.accessGranted === false || response.decision === 'ACCESS_DENIED') {
      this.doorStatus = 'denied';
    } else if (this.doorRelayEnabled && !response.duplicate) {
      // UNIFIED_HYBRID / enableDoorRelayOnAttendance: attendance success implies relay attempt.
      this.doorStatus = 'unlocked';
    }

    const identityType = String(response.identityType || '').toUpperCase();
    if (identityType === 'VIP' || response.decision === 'VIP_GREET') {
      this.vipArrivalName =
        response.subjectName || response.employee?.fullName || response.member?.fullName || 'VIP';
    }
    if (response.welcomeMessage) {
      this.welcomeBanner = String(response.welcomeMessage);
    }
    if (response.seatNumber != null && response.seatNumber !== '') {
      this.seatNumber = String(response.seatNumber);
    }
  }

  private updateTracks(detections: SmoothBox[], now: number) {
    detections = nmsBoxesHelper(detections, this.nmsIou);
    const usedDet = new Set<number>();
    const matchedTrackIds = new Set<number>();

    // Prefer older / identified tracks so a fleeting new box cannot steal identity.
    const ordered = [...this.tracks].sort((a, b) => {
      const aId = a.memberId ? 1 : 0;
      const bId = b.memberId ? 1 : 0;
      if (aId !== bId) {
        return bId - aId;
      }
      return a.firstSeenAt - b.firstSeenAt;
    });

    for (const track of ordered) {
      let bestIdx = -1;
      let bestScore = 0;
      // Match against last detection (target), not the lagging render box.
      const anchor = track.targetBox;
      for (let i = 0; i < detections.length; i++) {
        if (usedDet.has(i)) {
          continue;
        }
        const score = this.matchScore(anchor, detections[i] as SmoothBox);
        if (score > bestScore) {
          bestScore = score;
          bestIdx = i;
        }
      }
      if (bestIdx >= 0 && bestScore > 0) {
        usedDet.add(bestIdx);
        matchedTrackIds.add(track.id);
        track.targetBox = { ...detections[bestIdx] };
        track.lastSeenAt = now;
      }
    }

    this.tracks = this.tracks.filter((track) => {
      if (matchedTrackIds.has(track.id)) {
        return true;
      }
      if (track.phase === 'capturing' || track.phase === 'checking_in') {
        // Keep briefly while request in flight even if face left frame
        return now - track.lastSeenAt < 2500;
      }
      if (now - track.lastSeenAt > this.trackMissTtlMs) {
        if (track.captureTimer) {
          clearInterval(track.captureTimer);
          track.captureTimer = null;
        }
        return false;
      }
      return true;
    });

    for (let i = 0; i < detections.length; i++) {
      if (usedDet.has(i)) {
        continue;
      }
      this.tracks.push({
        id: this.nextTrackId++,
        box: { ...detections[i] },
        targetBox: { ...detections[i] },
        firstSeenAt: now,
        lastSeenAt: now,
        label: null,
        memberId: null,
        confidence: null,
        phase: 'watching',
        lastIdentifyAt: 0,
        identifyInFlight: false,
        captureFrames: [],
        captureTimer: null,
        retryAfter: 0,
        statusText: null,
      });
    }

    this.mergeOverlappingTracks();
  }

  private matchScore(a: SmoothBox, b: SmoothBox): number {
    return matchScoreHelper(a, b, {
      iouMatchMin: this.iouMatchMin,
      centerMatchMax: this.centerMatchMax,
    });
  }

  /** Collapse ghost tracks that still overlap after a motion miss. */
  private mergeOverlappingTracks(): void {
    if (this.tracks.length <= 1) {
      return;
    }
    const drop = new Set<number>();
    for (let i = 0; i < this.tracks.length; i++) {
      if (drop.has(this.tracks[i].id)) {
        continue;
      }
      for (let j = i + 1; j < this.tracks.length; j++) {
        if (drop.has(this.tracks[j].id)) {
          continue;
        }
        const a = this.tracks[i];
        const b = this.tracks[j];
        if (iou(a.targetBox, b.targetBox) < this.trackMergeIou && iou(a.box, b.box) < this.trackMergeIou) {
          continue;
        }
        // Keep the richer / older track.
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
        if (lose.captureTimer) {
          clearInterval(lose.captureTimer);
          lose.captureTimer = null;
        }
        drop.add(lose.id);
      }
    }
    if (drop.size > 0) {
      this.tracks = this.tracks.filter((t) => !drop.has(t.id));
    }
  }

  private drawAllTracks(displaySize: { width: number; height: number }) {
    const ctx = this.canvas.nativeElement.getContext('2d') as CanvasRenderingContext2D;
    ctx.clearRect(0, 0, displaySize.width, displaySize.height);
    for (const track of this.tracks) {
      const onCooldown = track.memberId ? this.isMemberOnCooldown(track.memberId) : false;
      const label =
        track.phase === 'checking_in' || track.phase === 'capturing'
          ? `${track.label || 'กำลังลงเวลา'}…`
          : onCooldown && track.label
            ? `${track.label} ✓`
            : track.label;
      drawSmoothOverlay(
        ctx,
        track.box,
        label,
        track.confidence,
        track.phase === 'done' || onCooldown,
        track.phase === 'capturing' || track.phase === 'checking_in',
      );
    }
  }

  private isMemberOnCooldown(memberId: string, now = Date.now()): boolean {
    const until = this.memberCooldownUntil.get(memberId) || 0;
    return now < until;
  }

  private setMemberCooldown(memberId: string, ms = this.memberCooldownMs) {
    this.memberCooldownUntil.set(memberId, Date.now() + ms);
  }

  private shouldIdentify(track: FaceTrack, now: number): boolean {
    if (track.identifyInFlight) {
      return false;
    }
    if (track.phase === 'capturing' || track.phase === 'checking_in') {
      return false;
    }
    if (track.box.width < this.minFaceWidth) {
      return false;
    }
    if (track.memberId && this.isMemberOnCooldown(track.memberId, now)) {
      track.phase = 'cooldown';
      return false;
    }
    // Already labeled — skip re-identify until the track is lost / replaced.
    if (track.memberId && track.label) {
      return false;
    }
    return now - track.lastIdentifyAt >= this.identifyEveryMs;
  }

  private shouldStartCheckIn(track: FaceTrack, now: number): boolean {
    if (this.gpsRequired && !this.hasValidLocation) {
      return false;
    }
    if (track.phase !== 'watching') {
      return false;
    }
    if (now < track.retryAfter) {
      return false;
    }
    if (this.checkInInFlight >= this.maxConcurrentCheckIn) {
      return false;
    }
    if (track.box.width < this.minFaceWidth) {
      return false;
    }
    if (now - track.firstSeenAt < this.autoStartHoldMs) {
      return false;
    }
    if (track.memberId && this.isMemberOnCooldown(track.memberId, now)) {
      track.phase = 'cooldown';
      return false;
    }
    return true;
  }

  private runTrackIdentify(track: FaceTrack) {
    track.identifyInFlight = true;
    track.lastIdentifyAt = Date.now();
    const trackId = track.id;
    const dataUrl = this.captureFaceCrop(track.box);
    if (!dataUrl) {
      track.identifyInFlight = false;
      return;
    }

    const requestId = this.nextWsRequestId(trackId);
    if (
      this.wsSend({
        type: 'identify',
        trackId,
        requestId,
        image: dataUrl,
      })
    ) {
      return;
    }

    // HTTP fallback — scoped to selected company; stationMode gates sentinel search (F3).
    const formData = new FormData();
    formData.append('file', this.dataURLtoFile(dataUrl, `live_${trackId}.jpg`));
    formData.append('companyId', this.companyId);
    formData.append('stationMode', this.stationMode);
    this.http.post(environment.baseUrl + `/face/members/identify`, formData).subscribe({
      next: (response: any) => {
        const t = this.tracks.find((x) => x.id === trackId);
        if (!t) {
          return;
        }
        t.identifyInFlight = false;
        t.memberId = response.memberId || response.member?.memberId || null;
        t.label = response.member?.fullName || response.member?.firstName || t.label;
        const confidence = Number(response.confidencePercent ?? NaN);
        t.confidence = Number.isFinite(confidence) ? confidence : null;
        if (t.memberId && this.isMemberOnCooldown(t.memberId)) {
          t.phase = 'cooldown';
        }
        this.cdr.detectChanges();
      },
      error: (error) => {
        const t = this.tracks.find((x) => x.id === trackId);
        if (t) {
          t.identifyInFlight = false;
        }
        if (error?.status === 403) {
          this.applyAccessDenied(t, false);
          this.cdr.detectChanges();
        }
      },
    });
  }

  private startTrackCapture(track: FaceTrack) {
    if (track.phase !== 'watching') {
      return;
    }
    track.phase = 'capturing';
    track.captureFrames = [];
    track.statusText = 'walkby';

    // Grab first crop immediately; with frameCount=1 send check-in without waiting.
    const first = this.captureFaceCrop(track.box);
    if (first) {
      track.captureFrames.push(first);
    }
    if (track.captureFrames.length >= this.frameCount) {
      this.sendTrackCheckIn(track);
      return;
    }

    track.captureTimer = setInterval(() => {
      const live = this.tracks.find((x) => x.id === track.id);
      if (!live) {
        if (track.captureTimer) {
          clearInterval(track.captureTimer);
        }
        return;
      }
      const crop = this.captureFaceCrop(live.box);
      if (crop) {
        live.captureFrames.push(crop);
      }
      if (live.captureFrames.length >= this.frameCount) {
        if (live.captureTimer) {
          clearInterval(live.captureTimer);
          live.captureTimer = null;
        }
        this.sendTrackCheckIn(live);
      }
    }, this.captureIntervalMs);
  }

  private sendTrackCheckIn(track: FaceTrack) {
    const frames = [...track.captureFrames];
    if (frames.length < 1) {
      track.phase = 'watching';
      track.retryAfter = Date.now() + this.retryFailMs;
      return;
    }
    if (stationModeRequiresGps(this.stationMode) && !this.hasValidLocation) {
      track.phase = 'watching';
      track.captureFrames = [];
      track.retryAfter = Date.now() + this.retryFailMs;
      this.notify('ยังไม่มีพิกัด GPS — รอเบราว์เซอร์อนุญาตตำแหน่งก่อนลงเวลา', 'warning');
      return;
    }

    track.phase = 'checking_in';
    this.checkInInFlight += 1;
    const trackId = track.id;
    const requestId = this.nextWsRequestId(trackId);
    const lat = this.location.latitude;
    const lng = this.location.longitude;
    const punchType = this.punchMode;
    const modeExtras = buildKioskCheckinExtras({
      stationMode: this.stationMode,
      zoneId: this.zoneId,
      eventId: this.eventId,
      enableDoorRelay: this.doorRelayEnabled,
      totpOrPin: this.zoneRequires2FA ? this.totpOrPin || null : null,
    });

    if (
      this.wsSend({
        type: 'checkin',
        trackId,
        requestId,
        images: frames,
        latitude: lat,
        longitude: lng,
        note: 'Face kiosk websocket walk-by',
        punchType,
        ...modeExtras,
      })
    ) {
      return;
    }

    // HTTP fallback
    const formData = new FormData();
    frames.forEach((dataUrl, index) => {
      formData.append('files', this.dataURLtoFile(dataUrl, `t${trackId}_${index}.jpg`));
    });
    formData.append('companyId', this.companyId);
    formData.append('latitude', String(lat));
    formData.append('longitude', String(lng));
    formData.append('note', 'Face kiosk walk-by check-in');
    formData.append('punchType', punchType);
    formData.append('stationMode', this.stationMode);
    if (this.zoneId) {
      formData.append('zoneId', this.zoneId);
    }
    if (this.eventId) {
      formData.append('eventId', this.eventId);
    }
    if (this.doorRelayEnabled) {
      formData.append('enableDoorRelay', 'true');
    }
    if (this.zoneRequires2FA && this.totpOrPin) {
      formData.append('totpOrPin', this.totpOrPin);
    }

    this.http.post(environment.baseUrl + this.checkInEndpoint, formData).subscribe({
      next: (response) => {
        this.checkInInFlight = Math.max(0, this.checkInInFlight - 1);
        const body = response as {
          memberId?: string;
          member?: { memberId?: string; fullName?: string };
          employee?: { fullName?: string };
          dedupeSeconds?: number;
          duplicate?: boolean;
        };
        const t = this.tracks.find((x) => x.id === trackId);
        const memberId = body.memberId || body.member?.memberId || t?.memberId;
        if (memberId) {
          const dedupeMs = body.dedupeSeconds
            ? Number(body.dedupeSeconds) * 1000
            : this.memberCooldownMs;
          this.setMemberCooldown(memberId, dedupeMs);
        }

        if (t) {
          t.phase = body.duplicate ? 'cooldown' : 'done';
          t.memberId = memberId || t.memberId;
          t.label = body.employee?.fullName || body.member?.fullName || t.label;
        }

        this.handleCheckInSuccess(body, frames, t, !!body.duplicate);
      },
      error: (error: { status?: number; error?: { detail?: string } }) => {
        this.checkInInFlight = Math.max(0, this.checkInInFlight - 1);
        const t = this.tracks.find((x) => x.id === trackId);
        if (t) {
          t.phase = 'watching';
          t.retryAfter = Date.now() + this.retryFailMs;
          t.captureFrames = [];
        }
        if (error?.status === 403) {
          this.applyAccessDenied(t, true);
        } else if (this.offlineQueue.isLikelyOffline(error)) {
          void this.enqueueOfflinePunch({
            images: frames,
            latitude: lat,
            longitude: lng,
            punchType,
            note: 'Face kiosk walk-by check-in (offline queue)',
            zoneId: this.zoneId,
            eventId: this.eventId,
            enableDoorRelay: this.doorRelayEnabled,
            totpOrPin: this.zoneRequires2FA ? this.totpOrPin || null : null,
          });
          if (t) {
            t.phase = 'done';
          }
        } else {
          const detail = error.error?.detail || 'Check-in failed';
          this.notify(`ข้ามใบหน้าหนึ่งรายการ: ${detail}`, 'warning');
        }
        this.cdr.detectChanges();
      },
    });
  }

  private handleCheckInSuccess(
    response: any,
    frames: string[],
    track: FaceTrack | undefined,
    isDuplicate = false,
  ) {
    this.applyStationModeResult(response);
    const employee = response.employee || {};
    const member = response.member || employee.member || {};
    // Prefer subjectName from modular decision engine when present.
    if (response.subjectName && !employee.fullName && !member.fullName) {
      employee.fullName = response.subjectName;
    }
    const ts = response.timestamp || {};
    const tsTypeRaw = ts.timestampType;
    const tsTypeNum =
      typeof tsTypeRaw === 'number'
        ? tsTypeRaw
        : typeof tsTypeRaw === 'string' && /^\d+$/.test(tsTypeRaw)
          ? Number(tsTypeRaw)
          : tsTypeRaw === 'WARNING' || tsTypeRaw === 'Warning'
            ? 0
            : tsTypeRaw === 'CHECK_OUT'
              ? 2
              : tsTypeRaw === 'BREAK_OUT'
                ? 4
                : tsTypeRaw === 'BREAK_IN'
                  ? 5
                  : 1;
    const isWarning = !!response.isWarning || tsTypeNum === 0;
    const isCheckOut = tsTypeNum === 2;
    const isBreakOut = tsTypeNum === 4;
    const isBreakIn = tsTypeNum === 5;
    const isLate = !!ts.isLate;
    const lateMinutes = Number(ts.lateMinutes || 0);
    const overtimeMinutes = Number(ts.overtimeMinutes || 0);
    const employeeName =
      employee.fullName ||
      member.fullName ||
      `${member.firstName || ''} ${member.lastName || ''}`.trim() ||
      track?.label ||
      'พนักงาน';
    const firstName =
      (member.firstName || employee.firstName || employeeName.split(/\s+/)[0] || '').trim();
    const employeeCode = employee.employeeId || member.username || '';
    const confidencePercent = Number(
      response.confidencePercent ?? ((1 - Number(response.distance || 0)) * 100),
    );
    const time = ts.timestamp ? new Date(ts.timestamp) : new Date();
    const timeLabel = time.toLocaleTimeString('th', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    const photoFile = ts.photoTimestamp || null;
    const photoUrl = photoFile
      ? this.authedImage(photoFile)
      : frames.length
        ? frames[Math.floor(frames.length / 2)]
        : ts.photoUrl
          ? `${environment.baseUrl || ''}${ts.photoUrl}`.replace(/([^:]\/)\/+/g, '$1')
          : null;

    if (track) {
      track.phase = isDuplicate ? 'cooldown' : 'done';
      track.label = employeeName;
      track.memberId = response.memberId || member.memberId || track.memberId;
      track.confidence = Number.isFinite(confidencePercent) ? confidencePercent : track.confidence;
    }

    let statusLabel = isWarning
      ? 'Warning — นอกพื้นที่'
      : isCheckOut
        ? overtimeMinutes > 0
          ? `ออกงาน (OT ${overtimeMinutes} นาที)`
          : 'ลงเวลาออกงาน'
        : isBreakOut
          ? 'พักนอก (Break-Out)'
          : isBreakIn
            ? 'พักเข้า (Break-In)'
            : isLate && lateMinutes > 0
              ? `เข้างาน (สาย ${lateMinutes} นาที)`
              : 'ลงเวลาเข้างาน';
    let statusKind: CheckInFeedItem['statusKind'] = isWarning || isLate ? 'warning' : 'success';
    if (isBreakOut || isBreakIn) {
      statusKind = 'info';
    }
    if (isDuplicate) {
      statusLabel = isWarning ? 'บันทึกแล้ว (Warning)' : 'ลงเวลาไปแล้ว';
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
      locationName: ts.locationName || (isWarning ? 'นอกพื้นที่ลงเวลา' : '-'),
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

    this.prependFeed(item);
    if (isDuplicate) {
      playDuplicateBeep();
    } else if (isWarning) {
      playWarningBeep();
    } else {
      playCheckInBeep();
    }
    const speechKey: TtsTemplateKey = isDuplicate
      ? 'checkInDuplicate'
      : isWarning
        ? 'checkInWarning'
        : 'checkInSuccess';
    this.speakCheckIn(speechKey, {
      name: employeeName,
      firstName,
      employeeId: employeeCode,
    });
    this.notify(
      isDuplicate
        ? `${employeeName} ลงเวลาไปแล้ว (ไม่บันทึกซ้ำ)`
        : isWarning
          ? `Warning: ${employeeName} (${item.confidencePercent?.toFixed(1) ?? '-'}%)`
          : `${statusLabel}: ${employeeName} (${item.confidencePercent?.toFixed(1) ?? '-'}%)`,
      isDuplicate ? 'info' : isWarning ? 'warning' : 'success',
    );
  }

  /** Crop face from live video using box in display (canvas) coordinates. */
  private captureFaceCrop(box: SmoothBox): string | null {
    const video = this.video.nativeElement as HTMLVideoElement;
    return captureFaceCropHelper(video, box, {
      cropPad: this.cropPad,
      displayWidth: video.width || 640,
      displayHeight: video.height || 480,
      videoWidth: video.videoWidth || video.width || 640,
      videoHeight: video.videoHeight || video.height || 480,
    });
  }

  private prependFeed(item: CheckInFeedItem) {
    this.ngZone.run(() => {
      this.latestResult = { ...item };
      this.feed = [item, ...this.feed.filter((f) => f.id !== item.id)].slice(0, 30);
      if (item.statusKind === 'success' || item.statusKind === 'warning' || item.statusKind === 'info') {
        this.loadAttendance();
      }
      this.cdr.detectChanges();
      // Mobile: bring result into view under the camera
      setTimeout(() => {
        const el = document.getElementById('dpu-kiosk-latest');
        el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 50);
    });
  }

  loadAttendance(): void {
    if (!this.companyId) return;
    this.http
      .get<KioskAttendance>(`${environment.baseUrl}/face/kiosk-attendance/${this.companyId}`)
      .subscribe({
        next: (data) => {
          this.ngZone.run(() => {
            this.attendance = data;
            this.cdr.detectChanges();
          });
        },
        error: (err) => {
          console.warn('kiosk attendance load failed', err);
        },
      });
  }

  trackByRosterId(_index: number, person: KioskRosterPerson): string {
    return person.company_employeeId || person.employeeId || String(_index);
  }

  trackByFeedId(_index: number, item: CheckInFeedItem): string {
    return item.id;
  }

  personPhoto(person: KioskRosterPerson): string {
    const file = person.photoTimestamp || person.picture;
    if (file) {
      return this.authedImage(file);
    }
    return './assets/images/faces/1.jpg';
  }

  /** Protected punch photo via Bearer-authenticated fetch → blob URL (no token in the URL). */
  private authedImage(file: string): string {
    return this.authedImages.urlFor(file, './assets/images/faces/1.jpg');
  }

  isOutside(person: KioskRosterPerson): boolean {
    return Number(person.timestampType) === 0;
  }

  isCheckedOut(person: KioskRosterPerson): boolean {
    return Number(person.timestampType) === 2;
  }

  private notify(message: string, kind: 'success' | 'warning' | 'error' | 'info') {
    this.toastMessage = message;
    this.toastKind = kind;
    this.showToast = true;
    if (this.toastTimer) {
      clearTimeout(this.toastTimer);
    }
    this.toastTimer = setTimeout(() => {
      this.showToast = false;
      this.cdr.detectChanges();
    }, 4000);
    this.cdr.detectChanges();
  }

  dataURLtoFile(dataurl: string, filename: string): File {
    return dataURLtoFileHelper(dataurl, filename);
  }

  private sendWsSession(): void {
    if (!this.wsConnected) {
      return;
    }
    this.wsSend(
      buildKioskSession({
        companyId: this.companyId,
        token: this.tokenService.getToken(),
        latitude: this.hasValidLocation ? this.location.latitude : undefined,
        longitude: this.hasValidLocation ? this.location.longitude : undefined,
        stationMode: this.stationMode,
        zoneId: this.zoneId,
        eventId: this.eventId,
      }),
    );
  }

  private applyGeoPosition(position: GeolocationPosition): void {
    this.location = {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
    };
    this.locationReady = this.hasValidLocation;
    this.searchCompanyLocation();
    this.errorMessage = null;
    this.sendWsSession();
    this.cdr.detectChanges();
  }

  /** Surface GPS failures loudly only when `stationModeRequiresGps`. */
  private applyGeoFailure(message: string, detail?: unknown): void {
    this.locationReady = false;
    if (this.gpsRequired) {
      this.errorMessage = message;
      console.error('Error fetching location:', message, detail);
    } else {
      // Access / watchlist / visitor / event — keep scanning; do not spam red GPS chrome.
      this.errorMessage = null;
      console.warn(`GPS unavailable (not required for ${this.stationMode}):`, message, detail);
    }
    this.cdr.detectChanges();
  }

  getCurrentLocation() {
    if (!navigator.geolocation) {
      this.applyGeoFailure('เบราว์เซอร์นี้ไม่รองรับ Geolocation');
      return;
    }

    // Secure context required (HTTPS or localhost). HTTP on LAN often yields no fix → stays 0,0.
    const host = window.location.hostname;
    if (!window.isSecureContext && host !== 'localhost' && host !== '127.0.0.1') {
      this.applyGeoFailure('ต้องเปิด kiosk ผ่าน HTTPS ถึงจะอ่าน GPS ได้ (ตอนนี้ไม่ใช่ secure context)');
    }

    const options: PositionOptions = {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 10000,
    };

    navigator.geolocation.getCurrentPosition(
      (position) => this.ngZone.run(() => this.applyGeoPosition(position)),
      (error) => {
        this.ngZone.run(() => {
          let message = 'ขอตำแหน่งไม่สำเร็จ';
          switch (error.code) {
            case error.PERMISSION_DENIED:
              message = 'ผู้ใช้ปฏิเสธการแชร์ตำแหน่ง — อนุญาต Location ในเบราว์เซอร์';
              break;
            case error.POSITION_UNAVAILABLE:
              message = 'อ่านตำแหน่งไม่ได้ (เครื่องไม่มี GPS / สัญญาณไม่พอ)';
              break;
            case error.TIMEOUT:
              message = 'ขอตำแหน่งหมดเวลา — กด Retry GPS หรือรีเฟรชหน้า';
              break;
            default:
              message = 'ขอตำแหน่งไม่สำเร็จ';
          }
          this.applyGeoFailure(message, error);
        });
      },
      options,
    );

    // Keep refreshing so kiosk does not stick on a stale/failed first read.
    if (this.geoWatchId == null) {
      this.geoWatchId = navigator.geolocation.watchPosition(
        (position) => this.ngZone.run(() => this.applyGeoPosition(position)),
        () => {
          /* keep last error from getCurrentPosition */
        },
        options,
      );
    }
  }

  private toRad(value: number): number {
    return (value * Math.PI) / 180;
  }

  getDistance(lat1: string, lon1: string, lat2: string, lon2: string): number {
    const R = 6371;
    const dLat = this.toRad(parseFloat(lat2) - parseFloat(lat1));
    const dLon = this.toRad(parseFloat(lon2) - parseFloat(lon1));
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.toRad(parseFloat(lat1))) *
        Math.cos(this.toRad(parseFloat(lat2))) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  searchCompanyLocation() {
    this.locationArea = this.getFilteredLocations();
  }

  getFilteredLocations(): CompanyLocationModel[] {
    return this.locationList.filter((location) => {
      const distance = this.getDistance(
        this.location.latitude.toString(),
        this.location.longitude.toString(),
        location.latitude.toString(),
        location.longitude.toString(),
      );
      return distance <= location.radius;
    });
  }
}
