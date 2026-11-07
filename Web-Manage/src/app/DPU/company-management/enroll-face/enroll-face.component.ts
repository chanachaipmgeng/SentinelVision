import { HttpClient } from '@angular/common/http';
import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, NgZone, OnDestroy, ViewChild } from '@angular/core';
import { RouterModule } from '@angular/router';
import { environment } from '../../../../environments/environment';
import { CommonModule } from '@angular/common';
import { TokenService } from '../../../shared/services/token.service';
import { AuthService } from '../../../shared/services/auth.service';
import { SharedModule } from '../../../shared/shared.module';
import { CompanyLocationModel } from '../../models/company-location.model';
import { CompanyLocationService } from '../../services/company-location.service';
import {
  playCheckInBeep,
  playDuplicateBeep,
  playWarningBeep,
  unlockBeepAudio,
} from '../../../shared/utils/beep';
import { speakText, unlockSpeech } from '../../../shared/utils/tts';
import {
  TtsSettings,
  TtsTemplateKey,
  buildSpeechText,
  resolveTtsSettings,
} from '../../../shared/utils/tts-templates';
import { SystemSettingService } from '../../services/system-setting.service';
import { buildKioskSession } from './kiosk-ws-client';
import {
  frameChangeScore,
  KIOSK_STATIC_SCENE_DIFF,
  nextCaptureInterval,
} from './kiosk-tracker.service';

// pace.js (theme progress bar) replaces window.WebSocket with a wrapper that
// drops static constants — `WebSocket.OPEN` is undefined at runtime. Compare
// readyState against these literals, never against `WebSocket.*`.
const WS_CONNECTING = 0;
const WS_OPEN = 1;

export type KioskPunchMode = 'AUTO' | 'CHECK_IN' | 'CHECK_OUT';

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

interface SmoothBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

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
  imports: [CommonModule, SharedModule, RouterModule],
  templateUrl: './enroll-face.component.html',
  styleUrl: './enroll-face.component.scss'
})
export class EnrollFaceComponent implements AfterViewInit, OnDestroy {
  @ViewChild('video') video: ElementRef;
  @ViewChild('canvas') canvas: ElementRef;
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

  /** Hybrid punch mode: AUTO (first scan = in, next = out) or explicit CHECK_IN / CHECK_OUT */
  punchMode: KioskPunchMode = 'AUTO';

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

  // Server-side detection (WS `detect`) — falls back to local face-api
  private wsDetectInFlight = false;
  private lastWsDetectAt = 0;
  private wsDetectMisses = 0;
  private serverDetectFailures = 0;
  private serverDetectPausedUntil = 0;
  private detectFrameCanvas: HTMLCanvasElement | null = null;
  private detectThumbCanvas: HTMLCanvasElement | null = null;
  private lastDetectThumb: Uint8ClampedArray | null = null;
  private lastDetectionsAt = 0;

  // Local face-api fallback health (devices without WebGL crash tfjs)
  private localDetectReady = false;
  private localDetectErrors = 0;
  private readonly memberCooldownUntil = new Map<string, number>();
  private checkInInFlight = 0;

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
  private readonly checkInEndpoint = '/face/members/check-in-walkby';

  constructor(
    private http: HttpClient,
    private tokenService: TokenService,
    private authService: AuthService,
    private comLocationService: CompanyLocationService,
    private systemSettingService: SystemSettingService,
    private ngZone: NgZone,
    private cdr: ChangeDetectorRef,
  ) {
    const company = this.tokenService.getSelectCompany();
    this.companyId = company.companyId;
    this.companyName = company.companyName || 'บริษัท';
    this.homeLink = `/company/home/${this.companyId}`;
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
        : mode === 'CHECK_OUT'
          ? 'โหมดออกงาน (Check-Out)'
          : 'โหมดอัตโนมัติ (Hybrid)';
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
    if (!this.locationReady) {
      return this.errorMessage ? 'ไม่มี GPS' : 'รอพิกัด…';
    }
    if (this.inArea) {
      return this.locationArea[0].locationName || 'ในพื้นที่';
    }
    return 'นอกพื้นที่';
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
    this.getCurrentLocation();
    unlockBeepAudio();
    unlockSpeech();
    this.loadTtsSettings();
    this.prepareLocalDetector();
    this.startVideo();
    this.getCompanyLocation();
    this.ngZone.runOutsideAngular(() => this.connectKioskWs());
    this.loadAttendance();
    this.ngZone.runOutsideAngular(() => {
      this.attendanceTimer = setInterval(() => {
        this.loadAttendance();
        this.loadTtsSettings();
      }, 15000);
    });
  }

  ngAfterViewInit(): void {
    this.startSceneClock();
  }

  /** Server WS detect is the only detector. Local face-api models are not shipped. */
  private async prepareLocalDetector(): Promise<void> {
    this.localDetectReady = false;
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
      dateEl.textContent = now.toLocaleDateString('en-GB', {
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
    const text = buildSpeechText(this.ttsSettings, key, vars);
    if (!text) return;
    speakText(text, {
      lang: this.ttsSettings.lang,
      rate: this.ttsSettings.rate,
      pitch: this.ttsSettings.pitch,
      cancelPrevious: true,
    });
  }

  ngOnDestroy() {
    document.documentElement.classList.remove('dpu-kiosk-mode');
    this.destroyWs = true;
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
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
      .then((stream) => {
        this.videoStream = stream;
        this.video.nativeElement.srcObject = stream;
        unlockBeepAudio();
        unlockSpeech();
      })
      .catch((err) => {
        console.error('Error accessing camera: ', err);
        this.captureMessage = 'ไม่สามารถเปิดกล้องได้';
        this.notify('ไม่สามารถเปิดกล้องได้', 'error');
      });
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
        if (this.wsConnected && this.wsSessionOk && nowMs >= this.serverDetectPausedUntil) {
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

    const vw = videoEl.videoWidth || 640;
    const vh = videoEl.videoHeight || 480;
    const targetW = 480;
    const scale = Math.min(1, targetW / vw);
    const w = Math.round(vw * scale);
    const h = Math.round(vh * scale);

    if (!this.detectFrameCanvas) {
      this.detectFrameCanvas = document.createElement('canvas');
    }
    const canvas = this.detectFrameCanvas;
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) {
      return;
    }
    ctx.drawImage(videoEl, 0, 0, w, h);

    // Thumbnail diff before JPEG encode — skip send when the scene is static.
    const thumb = this.sampleDetectThumb(canvas);
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

  /** 32×24 RGBA sample used for motion gating (cheap vs JPEG). */
  private sampleDetectThumb(source: HTMLCanvasElement): Uint8ClampedArray {
    if (!this.detectThumbCanvas) {
      this.detectThumbCanvas = document.createElement('canvas');
      this.detectThumbCanvas.width = 32;
      this.detectThumbCanvas.height = 24;
    }
    const thumb = this.detectThumbCanvas;
    const tctx = thumb.getContext('2d', { willReadFrequently: true });
    if (!tctx) {
      return new Uint8ClampedArray(32 * 24 * 4);
    }
    tctx.drawImage(source, 0, 0, 32, 24);
    return new Uint8ClampedArray(tctx.getImageData(0, 0, 32, 24).data);
  }

  /** Server detection result → display-space boxes → shared pipeline. */
  private onServerDetected(msg: any): void {
    this.wsDetectInFlight = false;
    this.wsDetectMisses = 0;
    this.serverDetectFailures = 0;
    if (msg?.queue?.pending != null) {
      this.queuePending = Number(msg.queue.pending) || 0;
    }

    const videoEl = this.video?.nativeElement as HTMLVideoElement | undefined;
    if (!videoEl) {
      return;
    }
    const frameW = Number(msg.frameWidth) || 1;
    const frameH = Number(msg.frameHeight) || 1;
    const displayW = videoEl.width || 640;
    const displayH = videoEl.height || 480;
    const sx = displayW / frameW;
    const sy = displayH / frameH;

    const boxes: SmoothBox[] = (Array.isArray(msg.faces) ? msg.faces : []).map((f: any) => ({
      x: Number(f.x) * sx,
      y: Number(f.y) * sy,
      width: Number(f.width) * sx,
      height: Number(f.height) * sy,
    }));
    this.processDetections(boxes, Date.now());
  }

  private onServerDetectError(): void {
    this.wsDetectInFlight = false;
    this.serverDetectFailures += 1;
    if (this.serverDetectFailures >= 3) {
      // Give the server a break; local face-api takes over meanwhile.
      this.serverDetectPausedUntil = Date.now() + 30000;
      this.serverDetectFailures = 0;
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
          const jump = this.boxCenterDist(track.box, track.targetBox);
          const sizeDelta =
            Math.abs(track.box.width - track.targetBox.width) +
            Math.abs(track.box.height - track.targetBox.height);
          const posT = jump > this.boxFastCenterPx ? this.boxFastPosLerp : this.boxPosLerp;
          const sizeT = sizeDelta > this.boxFastSizePx ? this.boxFastSizeLerp : this.boxSizeLerp;
          track.box = this.lerpBox(track.box, track.targetBox, posT, sizeT);
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
    if (!this.hasValidLocation) {
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
    const base = environment.baseUrl || `${window.location.protocol}//${window.location.host}`;
    const url = new URL(base, window.location.origin);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    url.pathname = '/face/ws/kiosk';
    url.search = '';
    url.hash = '';
    return url.toString();
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
    if (!this.kioskWs || this.kioskWs.readyState !== WS_OPEN) {
      return false;
    }
    // Only `session` may go out before the server acknowledges it (otherwise it closes with 1008).
    if (payload['type'] !== 'session' && !this.wsSessionOk) {
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
    this.authService.refreshToken(refresh.replace('Bearer ', '')).subscribe({
      next: (token) => {
        if (token?.accessToken) {
          this.tokenService.saveToken(token.accessToken);
        }
        if (token?.refreshToken) {
          this.tokenService.saveRefreshToken(token.refreshToken);
        }
        this.sendWsSession();
      },
    });
  }

  private onKioskWsMessage(msg: any) {
    if (msg?.queue?.pending != null) {
      this.queuePending = Number(msg.queue.pending) || 0;
    }

    if (msg.type === 'session_ok') {
      this.wsSessionOk = true;
      this.cdr.detectChanges();
      return;
    }

    if (msg.type === 'token_expiring') {
      this.refreshKioskToken();
      return;
    }

    if (msg.type === 'error' && msg.code === 'invalid_session') {
      // Server closes the socket after this; refresh the token so the reconnect's `session` is valid.
      this.wsSessionOk = false;
      this.refreshKioskToken();
      return;
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
        if (msg.detail) {
          this.notify(`ข้ามใบหน้าหนึ่งรายการ: ${msg.detail}`, 'warning');
        }
      }
      this.cdr.detectChanges();
    }
  }

  private updateTracks(detections: SmoothBox[], now: number) {
    detections = this.nmsBoxes(detections, this.nmsIou);
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
        const score = this.matchScore(anchor, detections[i]);
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

  /** Drop overlapping detections so one face cannot spawn multiple tracks. */
  private nmsBoxes(boxes: SmoothBox[], iouThresh: number): SmoothBox[] {
    if (boxes.length <= 1) {
      return boxes;
    }
    const sorted = [...boxes].sort((a, b) => b.width * b.height - a.width * a.height);
    const kept: SmoothBox[] = [];
    for (const box of sorted) {
      if (kept.every((k) => this.iou(k, box) < iouThresh)) {
        kept.push(box);
      }
    }
    return kept;
  }

  /**
   * Combined IoU + center proximity. Returns 0 when neither criterion matches.
   * Higher is better; used only for ranking among candidates that pass thresholds.
   */
  private matchScore(a: SmoothBox, b: SmoothBox): number {
    const iou = this.iou(a, b);
    if (iou >= this.iouMatchMin) {
      return 1 + iou;
    }
    const diag = (this.boxDiagonal(a) + this.boxDiagonal(b)) / 2;
    if (diag <= 1) {
      return 0;
    }
    const norm = this.boxCenterDist(a, b) / diag;
    if (norm <= this.centerMatchMax) {
      return 0.5 + (1 - norm / this.centerMatchMax) * 0.5;
    }
    return 0;
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
        if (this.iou(a.targetBox, b.targetBox) < this.trackMergeIou && this.iou(a.box, b.box) < this.trackMergeIou) {
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

  private iou(a: SmoothBox, b: SmoothBox): number {
    const x1 = Math.max(a.x, b.x);
    const y1 = Math.max(a.y, b.y);
    const x2 = Math.min(a.x + a.width, b.x + b.width);
    const y2 = Math.min(a.y + a.height, b.y + b.height);
    const inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
    const union = a.width * a.height + b.width * b.height - inter;
    return union > 0 ? inter / union : 0;
  }

  private boxCenterDist(a: SmoothBox, b: SmoothBox): number {
    const ax = a.x + a.width / 2;
    const ay = a.y + a.height / 2;
    const bx = b.x + b.width / 2;
    const by = b.y + b.height / 2;
    return Math.hypot(ax - bx, ay - by);
  }

  private boxDiagonal(b: SmoothBox): number {
    return Math.hypot(b.width, b.height);
  }

  /**
   * Ease toward the target around the face center so expand/shrink
   * stays locked on the subject instead of sliding from the top-left.
   */
  private lerpBox(prev: SmoothBox, next: SmoothBox, posT: number, sizeT: number): SmoothBox {
    const pcx = prev.x + prev.width * 0.5;
    const pcy = prev.y + prev.height * 0.5;
    const ncx = next.x + next.width * 0.5;
    const ncy = next.y + next.height * 0.5;
    const cx = pcx + (ncx - pcx) * posT;
    const cy = pcy + (ncy - pcy) * posT;
    const width = prev.width + (next.width - prev.width) * sizeT;
    const height = prev.height + (next.height - prev.height) * sizeT;
    return {
      x: cx - width * 0.5,
      y: cy - height * 0.5,
      width,
      height,
    };
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
      this.drawSmoothOverlay(
        ctx,
        track.box,
        label,
        track.confidence,
        track.phase === 'done' || onCooldown,
        track.phase === 'capturing' || track.phase === 'checking_in',
      );
    }
  }

  private drawSmoothOverlay(
    ctx: CanvasRenderingContext2D,
    box: SmoothBox,
    label: string | null,
    confidence: number | null,
    done: boolean,
    busy: boolean,
  ) {
    const pad = 5;
    const x = box.x - pad;
    const y = box.y - pad;
    const w = box.width + pad * 2;
    const h = box.height + pad * 2;
    const radius = 18;

    // Neon blue scan frame — single rounded stroke (no corner brackets / double border).
    let stroke = '#38bdf8';
    let glow = 'rgba(56, 189, 248, 0.85)';
    let labelBg = 'rgba(8, 47, 73, 0.88)';
    let labelFg = '#e0f2fe';
    if (done) {
      stroke = '#67e8f9';
      glow = 'rgba(103, 232, 249, 0.95)';
      labelBg = 'rgba(8, 47, 73, 0.92)';
      labelFg = '#ecfeff';
    } else if (busy) {
      stroke = '#7dd3fc';
      glow = 'rgba(125, 211, 252, 0.9)';
      labelBg = 'rgba(12, 74, 110, 0.9)';
      labelFg = '#f0f9ff';
    } else if (label) {
      stroke = '#22d3ee';
      glow = 'rgba(34, 211, 238, 0.95)';
      labelBg = 'rgba(8, 47, 73, 0.9)';
      labelFg = '#ecfeff';
    }

    ctx.save();
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 2.75;
    ctx.shadowColor = glow;
    ctx.shadowBlur = 16;
    this.roundRect(ctx, x, y, w, h, radius);
    ctx.stroke();
    ctx.shadowBlur = 0;

    if (label) {
      const text = confidence != null && !busy && !done
        ? `${label}  ${confidence.toFixed(0)}%`
        : label;
      ctx.font = '600 14px "Segoe UI", system-ui, sans-serif';
      const metrics = ctx.measureText(text);
      const labelPadX = 10;
      const labelH = 24;
      const labelW = metrics.width + labelPadX * 2;
      const labelX = x;
      const labelY = Math.max(8, y - labelH - 8);

      ctx.shadowColor = glow;
      ctx.shadowBlur = 10;
      ctx.fillStyle = labelBg;
      this.roundRect(ctx, labelX, labelY, labelW, labelH, 10);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      this.roundRect(ctx, labelX, labelY, labelW, labelH, 10);
      ctx.stroke();
      ctx.fillStyle = labelFg;
      ctx.textBaseline = 'middle';
      ctx.fillText(text, labelX + labelPadX, labelY + labelH / 2 + 1);
    }
    ctx.restore();
  }

  private roundRect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    w: number,
    h: number,
    r: number,
  ) {
    const radius = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + w, y, x + w, y + h, radius);
    ctx.arcTo(x + w, y + h, x, y + h, radius);
    ctx.arcTo(x, y + h, x, y, radius);
    ctx.arcTo(x, y, x + w, y, radius);
    ctx.closePath();
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
    if (!this.hasValidLocation) {
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

    // HTTP fallback — scoped to selected company
    const formData = new FormData();
    formData.append('file', this.dataURLtoFile(dataUrl, `live_${trackId}.jpg`));
    formData.append('companyId', this.companyId);
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
      error: () => {
        const t = this.tracks.find((x) => x.id === trackId);
        if (t) {
          t.identifyInFlight = false;
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
    if (!this.hasValidLocation) {
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

    this.http.post(environment.baseUrl + this.checkInEndpoint, formData).subscribe({
      next: (response: any) => {
        this.checkInInFlight = Math.max(0, this.checkInInFlight - 1);
        const t = this.tracks.find((x) => x.id === trackId);
        const memberId = response.memberId || response.member?.memberId || t?.memberId;
        if (memberId) {
          const dedupeMs = response.dedupeSeconds
            ? Number(response.dedupeSeconds) * 1000
            : this.memberCooldownMs;
          this.setMemberCooldown(memberId, dedupeMs);
        }

        if (t) {
          t.phase = response.duplicate ? 'cooldown' : 'done';
          t.memberId = memberId || t.memberId;
          t.label = response.employee?.fullName || response.member?.fullName || t.label;
        }

        this.handleCheckInSuccess(response, frames, t, !!response.duplicate);
      },
      error: (error) => {
        this.checkInInFlight = Math.max(0, this.checkInInFlight - 1);
        const t = this.tracks.find((x) => x.id === trackId);
        if (t) {
          t.phase = 'watching';
          t.retryAfter = Date.now() + this.retryFailMs;
          t.captureFrames = [];
        }
        const detail = error.error?.detail || 'Check-in failed';
        this.notify(`ข้ามใบหน้าหนึ่งรายการ: ${detail}`, 'warning');
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
    const employee = response.employee || {};
    const member = response.member || employee.member || {};
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
              : 1;
    const isWarning = !!response.isWarning || tsTypeNum === 0;
    const isCheckOut = tsTypeNum === 2;
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
        : isLate && lateMinutes > 0
          ? `เข้างาน (สาย ${lateMinutes} นาที)`
          : 'ลงเวลาเข้างาน';
    let statusKind: CheckInFeedItem['statusKind'] = isWarning || isLate ? 'warning' : 'success';
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
    const vw = video.videoWidth || video.width || 640;
    const vh = video.videoHeight || video.height || 480;
    const dw = video.width || 640;
    const dh = video.height || 480;

    const padX = box.width * this.cropPad;
    const padY = box.height * this.cropPad;
    let x = ((box.x - padX) / dw) * vw;
    let y = ((box.y - padY) / dh) * vh;
    let w = ((box.width + padX * 2) / dw) * vw;
    let h = ((box.height + padY * 2) / dh) * vh;

    x = Math.max(0, Math.min(x, vw - 2));
    y = Math.max(0, Math.min(y, vh - 2));
    w = Math.max(32, Math.min(w, vw - x));
    h = Math.max(32, Math.min(h, vh - y));

    const out = Math.max(160, Math.min(320, Math.round(Math.max(w, h))));
    const canvas = document.createElement('canvas');
    canvas.width = out;
    canvas.height = out;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return null;
    }
    ctx.drawImage(video, x, y, w, h, 0, 0, out, out);
    return canvas.toDataURL('image/jpeg', 0.88);
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

  private authedImage(file: string): string {
    const base = `${environment.baseUrl || ''}/images/${file}`.replace(/([^:]\/)\/+/g, '$1');
    const token = this.tokenService.getToken();
    return token ? `${base}?token=${encodeURIComponent(token)}` : base;
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
    const arr: any = dataurl.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: mime });
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

  getCurrentLocation() {
    if (!navigator.geolocation) {
      this.locationReady = false;
      this.errorMessage = 'เบราว์เซอร์นี้ไม่รองรับ Geolocation';
      return;
    }

    // Secure context required (HTTPS or localhost). HTTP on LAN often yields no fix → stays 0,0.
    const host = window.location.hostname;
    if (!window.isSecureContext && host !== 'localhost' && host !== '127.0.0.1') {
      this.locationReady = false;
      this.errorMessage = 'ต้องเปิด kiosk ผ่าน HTTPS ถึงจะอ่าน GPS ได้ (ตอนนี้ไม่ใช่ secure context)';
      console.error(this.errorMessage);
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
          this.locationReady = false;
          switch (error.code) {
            case error.PERMISSION_DENIED:
              this.errorMessage = 'ผู้ใช้ปฏิเสธการแชร์ตำแหน่ง — อนุญาต Location ในเบราว์เซอร์';
              break;
            case error.POSITION_UNAVAILABLE:
              this.errorMessage = 'อ่านตำแหน่งไม่ได้ (เครื่องไม่มี GPS / สัญญาณไม่พอ)';
              break;
            case error.TIMEOUT:
              this.errorMessage = 'ขอตำแหน่งหมดเวลา — ลองรีเฟรชหน้า';
              break;
            default:
              this.errorMessage = 'ขอตำแหน่งไม่สำเร็จ';
          }
          console.error('Error fetching location:', this.errorMessage, error);
          this.cdr.detectChanges();
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
