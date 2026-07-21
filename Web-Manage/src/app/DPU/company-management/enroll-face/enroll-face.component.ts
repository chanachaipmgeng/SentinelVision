import { HttpClient } from '@angular/common/http';
import { ChangeDetectorRef, Component, ElementRef, NgZone, OnDestroy, ViewChild } from '@angular/core';
import * as faceapi from 'face-api.js';

import { environment } from '../../../../environments/environment';
import { CommonModule } from '@angular/common';
import { TokenService } from '../../../shared/services/token.service';
import { SharedModule } from '../../../shared/shared.module';
import { CompanyLocationModel } from '../../models/company-location.model';
import { CompanyLocationService } from '../../services/company-location.service';

export interface CheckInFeedItem {
  id: string;
  employeeName: string;
  employeeId: string;
  department: string;
  position: string;
  statusLabel: string;
  statusKind: 'success' | 'warning' | 'error';
  locationName: string;
  timestamp: Date;
  photoUrl: string | null;
  message: string;
  confidencePercent?: number | null;
  matchQuality?: string | null;
  distance?: number | null;
}

interface SmoothBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

type TrackPhase = 'watching' | 'capturing' | 'checking_in' | 'done' | 'cooldown';

interface FaceTrack {
  id: number;
  box: SmoothBox;
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
  imports: [CommonModule, SharedModule],
  templateUrl: './enroll-face.component.html',
  styleUrl: './enroll-face.component.scss'
})
export class EnrollFaceComponent implements OnDestroy {
  @ViewChild('video') video: ElementRef;
  @ViewChild('canvas') canvas: ElementRef;
  locationList: CompanyLocationModel[] = [];
  locationArea: CompanyLocationModel[] = [];
  companyId = '';
  location: { latitude: number; longitude: number } = { latitude: 0, longitude: 0 };
  errorMessage: string | null = null;

  captureMessage = 'โหมด walk-by — หลายคนเดินผ่านได้ ลงเวลาเร็วโดยไม่ต้องขยับหน้า';
  activeFaceCount = 0;
  checkingInCount = 0;
  toastMessage = '';
  toastKind: 'success' | 'warning' | 'error' | 'info' = 'info';
  showToast = false;

  feed: CheckInFeedItem[] = [];
  latestResult: CheckInFeedItem | null = null;

  private faceDetectionInterval: ReturnType<typeof setInterval> | null = null;
  private videoStream: MediaStream | null = null;
  private toastTimer: ReturnType<typeof setTimeout> | null = null;
  private detectBusy = false;

  private tracks: FaceTrack[] = [];
  private nextTrackId = 1;
  private readonly memberCooldownUntil = new Map<string, number>();
  private checkInInFlight = 0;

  private readonly boxLerp = 0.4;
  private readonly iouMatchMin = 0.28;
  private readonly trackMissTtlMs = 450;
  /** Shorter hold for walk-by (no head-motion wait). */
  private readonly autoStartHoldMs = 320;
  private readonly memberCooldownMs = 5 * 60 * 1000;
  private readonly identifyEveryMs = 1200;
  /** Walk-by: 1–2 quality crops, no multi-frame motion liveness. */
  private readonly frameCount = 2;
  private readonly captureIntervalMs = 90;
  private readonly maxConcurrentCheckIn = 3;
  private readonly maxConcurrentIdentify = 2;
  private readonly minFaceWidth = 48;
  private readonly cropPad = 0.4;
  private readonly retryFailMs = 1800;
  private readonly checkInEndpoint = '/face/members/check-in-walkby';

  constructor(
    private http: HttpClient,
    private tokenService: TokenService,
    private comLocationService: CompanyLocationService,
    private ngZone: NgZone,
    private cdr: ChangeDetectorRef,
  ) {
    this.companyId = this.tokenService.getSelectCompany().companyId;
  }

  ngOnInit() {
    this.getCurrentLocation();
    faceapi.nets.tinyFaceDetector.loadFromUri('/assets/models/tiny_face_detector');
    this.startVideo();
    this.getCompanyLocation();
  }

  ngOnDestroy() {
    if (this.faceDetectionInterval) {
      clearInterval(this.faceDetectionInterval);
    }
    if (this.toastTimer) {
      clearTimeout(this.toastTimer);
    }
    for (const track of this.tracks) {
      if (track.captureTimer) {
        clearInterval(track.captureTimer);
      }
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
    faceapi.matchDimensions(this.canvas.nativeElement, displaySize);

    if (this.faceDetectionInterval) {
      clearInterval(this.faceDetectionInterval);
    }

    this.faceDetectionInterval = setInterval(async () => {
      if (this.detectBusy || !videoEl.srcObject || videoEl.readyState < 2) {
        return;
      }
      this.detectBusy = true;

      try {
        const detections = await faceapi.detectAllFaces(
          videoEl,
          new faceapi.TinyFaceDetectorOptions({ inputSize: 416, scoreThreshold: 0.45 }),
        );
        const resized = faceapi.resizeResults(detections, displaySize);
        const now = Date.now();
        const boxes: SmoothBox[] = resized.map((d) => ({
          x: d.box.x,
          y: d.box.y,
          width: d.box.width,
          height: d.box.height,
        }));

        this.updateTracks(boxes, now);
        this.drawAllTracks(displaySize);

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

        this.ngZone.run(() => {
          this.activeFaceCount = this.tracks.length;
          this.checkingInCount = this.tracks.filter(
            (t) => t.phase === 'capturing' || t.phase === 'checking_in',
          ).length;
          this.captureMessage = this.buildStatusMessage();
          this.cdr.detectChanges();
        });
      } catch (e) {
        console.error('detectFace error', e);
      } finally {
        this.detectBusy = false;
      }
    }, 90);
  }

  private buildStatusMessage(): string {
    if (this.tracks.length === 0) {
      return 'โหมด walk-by — เดินผ่านกล้องได้หลายคนพร้อมกัน';
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
    return parts.join(' · ');
  }

  private updateTracks(detections: SmoothBox[], now: number) {
    const usedDet = new Set<number>();
    const matchedTrackIds = new Set<number>();

    for (const track of this.tracks) {
      let bestIdx = -1;
      let bestIou = this.iouMatchMin;
      for (let i = 0; i < detections.length; i++) {
        if (usedDet.has(i)) {
          continue;
        }
        const score = this.iou(track.box, detections[i]);
        if (score > bestIou) {
          bestIou = score;
          bestIdx = i;
        }
      }
      if (bestIdx >= 0) {
        usedDet.add(bestIdx);
        matchedTrackIds.add(track.id);
        track.box = this.lerpBox(track.box, detections[bestIdx], this.boxLerp);
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

  private lerpBox(prev: SmoothBox, next: SmoothBox, t: number): SmoothBox {
    return {
      x: prev.x + (next.x - prev.x) * t,
      y: prev.y + (next.y - prev.y) * t,
      width: prev.width + (next.width - prev.width) * t,
      height: prev.height + (next.height - prev.height) * t,
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
    const pad = 6;
    const x = box.x - pad;
    const y = box.y - pad;
    const w = box.width + pad * 2;
    const h = box.height + pad * 2;
    const radius = 14;

    let stroke = 'rgba(148, 163, 184, 0.9)';
    let corner = '#94a3b8';
    let labelBg = 'rgba(51, 65, 85, 0.92)';
    if (done) {
      stroke = 'rgba(52, 211, 153, 0.95)';
      corner = '#34d399';
      labelBg = 'rgba(6, 95, 70, 0.92)';
    } else if (busy) {
      stroke = 'rgba(251, 191, 36, 0.95)';
      corner = '#fbbf24';
      labelBg = 'rgba(146, 64, 14, 0.92)';
    } else if (label) {
      stroke = 'rgba(45, 212, 191, 0.95)';
      corner = '#5eead4';
      labelBg = 'rgba(15, 118, 110, 0.92)';
    }

    ctx.save();
    ctx.lineWidth = 3;
    ctx.strokeStyle = stroke;
    ctx.shadowColor = stroke;
    ctx.shadowBlur = 8;
    this.roundRect(ctx, x, y, w, h, radius);
    ctx.stroke();
    ctx.shadowBlur = 0;

    const c = Math.min(28, w * 0.22, h * 0.22);
    ctx.lineWidth = 4;
    ctx.strokeStyle = corner;
    ctx.beginPath();
    ctx.moveTo(x, y + c);
    ctx.lineTo(x, y);
    ctx.lineTo(x + c, y);
    ctx.moveTo(x + w - c, y);
    ctx.lineTo(x + w, y);
    ctx.lineTo(x + w, y + c);
    ctx.moveTo(x + w, y + h - c);
    ctx.lineTo(x + w, y + h);
    ctx.lineTo(x + w - c, y + h);
    ctx.moveTo(x + c, y + h);
    ctx.lineTo(x, y + h);
    ctx.lineTo(x, y + h - c);
    ctx.stroke();

    if (label) {
      const text = confidence != null && !busy && !done
        ? `${label}  ${confidence.toFixed(0)}%`
        : label;
      ctx.font = '600 15px "Segoe UI", system-ui, sans-serif';
      const metrics = ctx.measureText(text);
      const labelPadX = 10;
      const labelH = 26;
      const labelW = metrics.width + labelPadX * 2;
      const labelX = x;
      const labelY = Math.max(8, y - labelH - 6);

      ctx.fillStyle = labelBg;
      this.roundRect(ctx, labelX, labelY, labelW, labelH, 8);
      ctx.fill();
      ctx.fillStyle = '#ecfdf5';
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
    return now - track.lastIdentifyAt >= this.identifyEveryMs;
  }

  private shouldStartCheckIn(track: FaceTrack, now: number): boolean {
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
    const formData = new FormData();
    formData.append('file', this.dataURLtoFile(dataUrl, `live_${trackId}.jpg`));

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

    // Grab first crop immediately, then 1 more shortly after
    const first = this.captureFaceCrop(track.box);
    if (first) {
      track.captureFrames.push(first);
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

    track.phase = 'checking_in';
    this.checkInInFlight += 1;
    const trackId = track.id;

    const formData = new FormData();
    frames.forEach((dataUrl, index) => {
      formData.append('files', this.dataURLtoFile(dataUrl, `t${trackId}_${index}.jpg`));
    });
    formData.append('companyId', this.companyId);
    formData.append('latitude', String(this.location?.latitude ?? 0));
    formData.append('longitude', String(this.location?.longitude ?? 0));
    formData.append('note', 'Face kiosk walk-by check-in');

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

        if (response.duplicate) {
          if (t) {
            t.phase = 'cooldown';
            t.memberId = memberId || t.memberId;
            t.label = response.employee?.fullName || response.member?.fullName || t.label;
            t.statusText = 'duplicate';
          }
          const name = response.employee?.fullName || response.member?.fullName || 'พนักงาน';
          this.notify(`${name} ลงเวลาไปแล้ว (ไม่บันทึกซ้ำ)`, 'info');
          this.cdr.detectChanges();
          return;
        }

        this.handleCheckInSuccess(response, frames, t);
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

  private handleCheckInSuccess(response: any, frames: string[], track: FaceTrack | undefined) {
    const employee = response.employee || {};
    const member = response.member || employee.member || {};
    const ts = response.timestamp || {};
    const isWarning = !!response.isWarning || Number(ts.timestampType) === 0;
    const employeeName =
      employee.fullName ||
      member.fullName ||
      `${member.firstName || ''} ${member.lastName || ''}`.trim() ||
      'พนักงาน';
    const confidencePercent = Number(
      response.confidencePercent ?? ((1 - Number(response.distance || 0)) * 100),
    );
    const time = ts.timestamp ? new Date(ts.timestamp) : new Date();
    const timeLabel = time.toLocaleTimeString('th', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    const photoUrl = ts.photoTimestamp
      ? `${environment.baseUrl}/images/${ts.photoTimestamp}`
      : frames[Math.floor(frames.length / 2)];

    if (track) {
      track.phase = 'done';
      track.label = employeeName;
      track.memberId = response.memberId || member.memberId || track.memberId;
      track.confidence = Number.isFinite(confidencePercent) ? confidencePercent : track.confidence;
    }

    const item: CheckInFeedItem = {
      id: ts.timestampId || `${Date.now()}`,
      employeeName,
      employeeId: employee.employeeId || '-',
      department: employee.department || '-',
      position: employee.position || '-',
      statusLabel: isWarning ? 'Warning — นอกพื้นที่' : 'ลงเวลาปกติ',
      statusKind: isWarning ? 'warning' : 'success',
      locationName: ts.locationName || (isWarning ? 'นอกพื้นที่ลงเวลา' : '-'),
      timestamp: time,
      photoUrl,
      message: `${employeeName} · ${timeLabel}`,
      confidencePercent: Number.isFinite(confidencePercent) ? confidencePercent : null,
      matchQuality: response.matchQuality ?? null,
      distance: response.distance != null ? Number(response.distance) : null,
    };

    this.prependFeed(item);
    this.notify(
      isWarning
        ? `Warning: ${employeeName} (${item.confidencePercent?.toFixed(1) ?? '-'}%)`
        : `ลงเวลาสำเร็จ: ${employeeName} (${item.confidencePercent?.toFixed(1) ?? '-'}%)`,
      isWarning ? 'warning' : 'success',
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
    this.latestResult = item;
    this.feed = [item, ...this.feed].slice(0, 30);
    this.cdr.detectChanges();
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

  getCurrentLocation() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          this.location = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          };
          this.searchCompanyLocation();
          this.errorMessage = null;
        },
        (error) => {
          switch (error.code) {
            case error.PERMISSION_DENIED:
              this.errorMessage = 'Permission denied by the user.';
              break;
            case error.POSITION_UNAVAILABLE:
              this.errorMessage = 'Location information is unavailable.';
              break;
            case error.TIMEOUT:
              this.errorMessage = 'The request to get user location timed out.';
              break;
            default:
              this.errorMessage = 'An unknown error occurred.';
          }
          console.error('Error fetching location:', this.errorMessage);
        },
      );
    } else {
      this.errorMessage = 'Geolocation is not supported by this browser.';
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
