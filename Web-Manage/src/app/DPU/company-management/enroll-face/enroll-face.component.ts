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
  checkMatch = false;
  companyId = '';
  location: { latitude: number; longitude: number } = { latitude: 0, longitude: 0 };
  errorMessage: string | null = null;

  isCapturing = false;
  captureProgress = 0;
  captureMessage = 'วางใบหน้าให้อยู่กลางจอ — ระบบจะลงเวลาอัตโนมัติ';
  toastMessage = '';
  toastKind: 'success' | 'warning' | 'error' | 'info' = 'info';
  showToast = false;

  feed: CheckInFeedItem[] = [];
  latestResult: CheckInFeedItem | null = null;

  /** Live overlay identity (from lightweight identify). */
  liveLabel: string | null = null;
  liveConfidence: number | null = null;

  private faceDetectionInterval: ReturnType<typeof setInterval> | null = null;
  private videoStream: MediaStream | null = null;
  private faceSeenSince: number | null = null;
  private cooldownUntil = 0;
  private toastTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly autoStartHoldMs = 700;
  private readonly cooldownMs = 7000;
  private readonly frameCount = 5;
  private readonly captureIntervalMs = 140;

  private smoothBox: SmoothBox | null = null;
  private readonly boxLerp = 0.38;
  private lastIdentifyAt = 0;
  private identifyInFlight = false;
  private identifyReqId = 0;
  private readonly identifyEveryMs = 1100;
  private faceLostSince: number | null = null;

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
    const videoEl = this.video.nativeElement;
    const displaySize = { width: videoEl.width, height: videoEl.height };
    faceapi.matchDimensions(this.canvas.nativeElement, displaySize);

    if (this.faceDetectionInterval) {
      clearInterval(this.faceDetectionInterval);
    }

    this.faceDetectionInterval = setInterval(async () => {
      if (!videoEl.srcObject || videoEl.readyState < 2) {
        return;
      }

      try {
        const detections = await faceapi.detectAllFaces(
          videoEl,
          new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.5 }),
        );
        const resized = faceapi.resizeResults(detections, displaySize);
        const ctx = this.canvas.nativeElement.getContext('2d') as CanvasRenderingContext2D;
        ctx.clearRect(0, 0, displaySize.width, displaySize.height);

        const now = Date.now();
        if (resized.length > 0) {
          this.faceLostSince = null;
          const box = resized[0].box;
          const target: SmoothBox = {
            x: box.x,
            y: box.y,
            width: box.width,
            height: box.height,
          };
          this.smoothBox = this.lerpBox(this.smoothBox, target, this.boxLerp);
          this.drawSmoothOverlay(ctx, this.smoothBox!, this.liveLabel, this.liveConfidence);

          if (
            !this.isCapturing &&
            now >= this.cooldownUntil &&
            !this.identifyInFlight &&
            now - this.lastIdentifyAt >= this.identifyEveryMs
          ) {
            this.lastIdentifyAt = now;
            this.runLiveIdentify();
          }
        } else {
          if (!this.faceLostSince) {
            this.faceLostSince = now;
          }
          if (this.smoothBox && this.faceLostSince && now - this.faceLostSince < 280) {
            this.drawSmoothOverlay(ctx, this.smoothBox, this.liveLabel, this.liveConfidence);
          } else {
            this.smoothBox = null;
            if (this.liveLabel) {
              this.ngZone.run(() => {
                this.liveLabel = null;
                this.liveConfidence = null;
                this.cdr.detectChanges();
              });
            }
          }
        }

        if (this.isCapturing) {
          return;
        }

        this.ngZone.run(() => {
          this.checkMatch = resized.length > 0;

          if (now < this.cooldownUntil) {
            const waitSec = Math.ceil((this.cooldownUntil - now) / 1000);
            this.captureMessage = `พร้อมสแกนคนถัดไปใน ${waitSec} วิ`;
            this.faceSeenSince = null;
            this.cdr.detectChanges();
            return;
          }

          if (this.checkMatch) {
            if (!this.faceSeenSince) {
              this.faceSeenSince = now;
            }
            const held = now - this.faceSeenSince;
            if (held >= this.autoStartHoldMs) {
              this.captureMessage = this.liveLabel
                ? `กำลังลงเวลา — ${this.liveLabel}`
                : 'พบใบหน้า — กำลังลงเวลาอัตโนมัติ';
              this.cdr.detectChanges();
              this.captureImage();
              return;
            }
            this.captureMessage = this.liveLabel
              ? `พบ ${this.liveLabel} — กำลังยืนยัน...`
              : 'พบใบหน้า — กำลังยืนยัน...';
          } else {
            this.faceSeenSince = null;
            this.captureMessage = 'วางใบหน้าให้อยู่กลางจอ — ระบบจะลงเวลาอัตโนมัติ';
          }
          this.cdr.detectChanges();
        });
      } catch (e) {
        console.error('detectFace error', e);
      }
    }, 100);
  }

  private lerpBox(prev: SmoothBox | null, next: SmoothBox, t: number): SmoothBox {
    if (!prev) {
      return { ...next };
    }
    return {
      x: prev.x + (next.x - prev.x) * t,
      y: prev.y + (next.y - prev.y) * t,
      width: prev.width + (next.width - prev.width) * t,
      height: prev.height + (next.height - prev.height) * t,
    };
  }

  private drawSmoothOverlay(
    ctx: CanvasRenderingContext2D,
    box: SmoothBox,
    label: string | null,
    confidence: number | null,
  ) {
    const pad = 6;
    const x = box.x - pad;
    const y = box.y - pad;
    const w = box.width + pad * 2;
    const h = box.height + pad * 2;
    const radius = 14;

    ctx.save();
    ctx.lineWidth = 3;
    ctx.strokeStyle = label ? 'rgba(45, 212, 191, 0.95)' : 'rgba(148, 163, 184, 0.9)';
    ctx.shadowColor = label ? 'rgba(45, 212, 191, 0.45)' : 'rgba(15, 23, 42, 0.35)';
    ctx.shadowBlur = 10;
    this.roundRect(ctx, x, y, w, h, radius);
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Corner accents
    const corner = Math.min(28, w * 0.22, h * 0.22);
    ctx.lineWidth = 4;
    ctx.strokeStyle = label ? '#5eead4' : '#94a3b8';
    ctx.beginPath();
    ctx.moveTo(x, y + corner);
    ctx.lineTo(x, y);
    ctx.lineTo(x + corner, y);
    ctx.moveTo(x + w - corner, y);
    ctx.lineTo(x + w, y);
    ctx.lineTo(x + w, y + corner);
    ctx.moveTo(x + w, y + h - corner);
    ctx.lineTo(x + w, y + h);
    ctx.lineTo(x + w - corner, y + h);
    ctx.moveTo(x + corner, y + h);
    ctx.lineTo(x, y + h);
    ctx.lineTo(x, y + h - corner);
    ctx.stroke();

    if (label) {
      const text = confidence != null
        ? `${label}  ${confidence.toFixed(0)}%`
        : label;
      ctx.font = '600 16px "Segoe UI", system-ui, sans-serif';
      const metrics = ctx.measureText(text);
      const labelPadX = 10;
      const labelH = 28;
      const labelW = metrics.width + labelPadX * 2;
      const labelX = x;
      const labelY = Math.max(8, y - labelH - 6);

      ctx.fillStyle = 'rgba(15, 118, 110, 0.92)';
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

  private runLiveIdentify() {
    this.identifyInFlight = true;
    const reqId = ++this.identifyReqId;
    const dataUrl = this.captureFrame();
    const formData = new FormData();
    formData.append('file', this.dataURLtoFile(dataUrl, 'live.jpg'));

    this.http.post(environment.baseUrl + `/face/members/identify`, formData).subscribe({
      next: (response: any) => {
        if (reqId !== this.identifyReqId) {
          return;
        }
        this.identifyInFlight = false;
        const name = response.member?.fullName || response.member?.firstName || null;
        const confidence = Number(response.confidencePercent ?? NaN);
        this.ngZone.run(() => {
          this.liveLabel = name;
          this.liveConfidence = Number.isFinite(confidence) ? confidence : null;
          this.cdr.detectChanges();
        });
      },
      error: () => {
        if (reqId !== this.identifyReqId) {
          return;
        }
        this.identifyInFlight = false;
        // Keep previous label briefly; clear only if we never had one
      },
    });
  }

  captureImage(): void {
    if (this.isCapturing || !this.checkMatch) {
      return;
    }

    this.isCapturing = true;
    this.faceSeenSince = null;
    this.captureProgress = 0;
    this.captureMessage = 'กำลังตรวจ liveness... กรุณาขยับใบหน้าเล็กน้อย';
    this.cdr.detectChanges();

    const capturedFrames: string[] = [];

    const captureProcess = setInterval(() => {
      if (capturedFrames.length >= this.frameCount) {
        clearInterval(captureProcess);
        this.sendCheckIn(capturedFrames);
        return;
      }

      const frame = this.captureFrame();
      capturedFrames.push(frame);
      this.ngZone.run(() => {
        this.captureProgress = (capturedFrames.length / this.frameCount) * 100;
        this.cdr.detectChanges();
      });
    }, this.captureIntervalMs);
  }

  captureFrame(): string {
    const video = this.video.nativeElement;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || video.width || 640;
    canvas.height = video.videoHeight || video.height || 480;
    const context = canvas.getContext('2d');
    context?.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.85);
  }

  sendCheckIn(frames: string[]): void {
    this.captureMessage = 'กำลังลงเวลา...';
    this.cdr.detectChanges();

    const formData = new FormData();
    frames.forEach((dataUrl, index) => {
      formData.append('files', this.dataURLtoFile(dataUrl, `frame_${index}.jpg`));
    });
    formData.append('companyId', this.companyId);
    formData.append('latitude', String(this.location?.latitude ?? 0));
    formData.append('longitude', String(this.location?.longitude ?? 0));
    formData.append('note', 'Face kiosk auto check-in');

    this.http.post(environment.baseUrl + `/face/members/check-in`, formData).subscribe({
      next: (response: any) => {
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

        this.liveLabel = employeeName;
        this.liveConfidence = item.confidencePercent ?? null;
        this.prependFeed(item);
        this.notify(
          isWarning
            ? `Warning: ${employeeName} (${item.confidencePercent?.toFixed(1) ?? '-'}%)`
            : `ลงเวลาสำเร็จ: ${employeeName} (${item.confidencePercent?.toFixed(1) ?? '-'}%)`,
          isWarning ? 'warning' : 'success',
        );
        this.captureMessage = isWarning
          ? `บันทึก Warning แล้ว — ${employeeName}`
          : `ลงเวลาสำเร็จ — ${employeeName}`;
        this.resetCaptureState(true);
      },
      error: (error) => {
        const detail = error.error?.detail || 'Check-in failed. Please try again.';
        this.pushErrorResult('ลงเวลาไม่สำเร็จ', detail);
        this.resetCaptureState(true);
      },
    });
  }

  private prependFeed(item: CheckInFeedItem) {
    this.latestResult = item;
    this.feed = [item, ...this.feed].slice(0, 20);
    this.cdr.detectChanges();
  }

  private pushErrorResult(title: string, detail: string) {
    const item: CheckInFeedItem = {
      id: `err-${Date.now()}`,
      employeeName: title,
      employeeId: '-',
      department: '-',
      position: '-',
      statusLabel: 'ไม่สำเร็จ',
      statusKind: 'error',
      locationName: '-',
      timestamp: new Date(),
      photoUrl: null,
      message: detail,
    };
    this.prependFeed(item);
    this.notify(`${title}: ${detail}`, 'error');
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
    }, 4500);
    this.cdr.detectChanges();
  }

  resetCaptureState(startCooldown = false) {
    this.isCapturing = false;
    this.captureProgress = 0;
    this.faceSeenSince = null;
    if (startCooldown) {
      this.cooldownUntil = Date.now() + this.cooldownMs;
      this.captureMessage = `พร้อมสแกนคนถัดไปใน ${Math.ceil(this.cooldownMs / 1000)} วิ`;
    } else {
      this.captureMessage = this.checkMatch
        ? (this.liveLabel ? `พบ ${this.liveLabel}` : 'พบใบหน้า — กำลังยืนยัน...')
        : 'วางใบหน้าให้อยู่กลางจอ — ระบบจะลงเวลาอัตโนมัติ';
    }
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
