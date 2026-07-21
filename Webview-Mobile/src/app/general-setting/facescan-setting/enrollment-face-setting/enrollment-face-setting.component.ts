import { HttpClient } from '@angular/common/http';
import { ChangeDetectorRef, Component, ElementRef, NgZone, OnDestroy, ViewChild } from '@angular/core';
import * as faceapi from 'face-api.js';
import { TokenService } from 'src/app/shared/services/token.service';
import { environment } from 'src/environments/environment';
import swal from 'sweetalert';
import { assetUrl } from 'src/app/shared/utils/asset-url';
import { playCaptureBeep, unlockBeepAudio } from 'src/app/shared/utils/beep';

interface SmoothBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface FaceAngleStep {
  id: 'front' | 'left' | 'right' | 'up' | 'down';
  label: string;
  hint: string;
  captured: boolean;
  preview: string | null;
}

@Component({
  selector: 'app-enrollment-face-setting',
  templateUrl: './enrollment-face-setting.component.html',
  styleUrls: ['./enrollment-face-setting.component.css']
})
export class EnrollmentFaceSettingComponent implements OnDestroy {
  @ViewChild('video') video: ElementRef;
  @ViewChild('canvas') canvas: ElementRef;
  capturedImage: string | null = null;
  uploadStatus = '';
  checkMatch = false;
  memberId = '';
  isFaceDetected = false;
  faceStatus = 'กำลังโหลดกล้อง...';
  isUploadingFace = false;
  uploadProgressLabel = '';
  faceAngleSteps: FaceAngleStep[] = [];
  currentAngleIndex = 0;

  private modelsLoaded = false;
  private faceDetectionInterval: ReturnType<typeof setInterval> | null = null;
  private videoStream: MediaStream | null = null;
  private smoothedBox: SmoothBox | null = null;
  private poseHoldStartedAt = 0;
  private capturingAngle = false;
  private readonly boxLerp = 0.35;
  private readonly poseHoldMs = 700;

  get currentAngle(): FaceAngleStep | null {
    return this.faceAngleSteps[this.currentAngleIndex] || null;
  }

  get capturedAngleCount(): number {
    return this.faceAngleSteps.filter((s) => s.captured).length;
  }

  get allAnglesCaptured(): boolean {
    return this.faceAngleSteps.length > 0 && this.capturedAngleCount === this.faceAngleSteps.length;
  }

  constructor(
    private http: HttpClient,
    private tokenService: TokenService,
    private ngZone: NgZone,
    private cdr: ChangeDetectorRef,
  ) {
    this.memberId = this.tokenService.getUser().member.memberId;
    this.resetFaceAngles();
  }

  async ngOnInit() {
    try {
      unlockBeepAudio();
      await this.ensureFaceModels();
      await this.startVideo();
      this.faceStatus = `มุม 1/5 — ${this.currentAngle?.hint}`;
      this.cdr.detectChanges();
      setTimeout(() => this.detectFace(), 300);
    } catch (err: any) {
      this.faceStatus = err?.message || 'เปิดกล้องไม่สำเร็จ';
      this.cdr.detectChanges();
    }
  }

  ngOnDestroy(): void {
    this.stopFaceCamera();
  }

  private resetFaceAngles(): void {
    this.currentAngleIndex = 0;
    this.faceAngleSteps = [
      { id: 'front', label: 'ตรง', hint: 'มองตรงกล้อง ใบหน้าอยู่กลางจอ', captured: false, preview: null },
      { id: 'left', label: 'ซ้าย', hint: 'หันหน้าไปทางซ้ายเล็กน้อย', captured: false, preview: null },
      { id: 'right', label: 'ขวา', hint: 'หันหน้าไปทางขวาเล็กน้อย', captured: false, preview: null },
      { id: 'up', label: 'เงย', hint: 'เงยหน้าขึ้นเล็กน้อย', captured: false, preview: null },
      { id: 'down', label: 'ก้ม', hint: 'ก้มหน้าลงเล็กน้อย', captured: false, preview: null },
    ];
  }

  private async ensureFaceModels(): Promise<void> {
    if (this.modelsLoaded) {
      return;
    }
    const modelsBase = assetUrl('assets/models');
    await Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri(`${modelsBase}/tiny_face_detector`),
      faceapi.nets.faceLandmark68Net.loadFromUri(`${modelsBase}/face_landmark_68`),
    ]);
    this.modelsLoaded = true;
  }

  startVideo(): Promise<void> {
    this.stopFaceCamera();
    return navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
    }).then((stream) => {
      this.videoStream = stream;
      if (this.video?.nativeElement) {
        this.video.nativeElement.srcObject = stream;
      }
    }).catch((err) => {
      console.error('Error accessing camera: ', err);
      throw new Error('ไม่สามารถเปิดกล้องได้');
    });
  }

  stopFaceCamera(): void {
    if (this.faceDetectionInterval) {
      clearInterval(this.faceDetectionInterval);
      this.faceDetectionInterval = null;
    }
    if (this.videoStream) {
      this.videoStream.getTracks().forEach((t) => t.stop());
      this.videoStream = null;
    }
    if (this.video?.nativeElement) {
      this.video.nativeElement.srcObject = null;
    }
  }

  async detectFace() {
    if (!this.video?.nativeElement || !this.canvas?.nativeElement) {
      return;
    }
    const videoEl = this.video.nativeElement;
    const displaySize = {
      width: videoEl.clientWidth || videoEl.width || 640,
      height: videoEl.clientHeight || videoEl.height || 480,
    };
    this.canvas.nativeElement.width = displaySize.width;
    this.canvas.nativeElement.height = displaySize.height;
    faceapi.matchDimensions(this.canvas.nativeElement, displaySize);

    if (this.faceDetectionInterval) {
      clearInterval(this.faceDetectionInterval);
    }

    this.faceDetectionInterval = setInterval(async () => {
      if (!videoEl.srcObject || videoEl.readyState < 2 || this.isUploadingFace) {
        return;
      }
      try {
        const detections = await faceapi
          .detectAllFaces(
            videoEl,
            new faceapi.TinyFaceDetectorOptions({ inputSize: 416, scoreThreshold: 0.45 }),
          )
          .withFaceLandmarks();
        const resized = faceapi.resizeResults(detections, displaySize);
        const ctx = this.canvas.nativeElement.getContext('2d') as CanvasRenderingContext2D;
        ctx.clearRect(0, 0, displaySize.width, displaySize.height);

        const best = resized[0];
        if (best) {
          const nextBox: SmoothBox = {
            x: best.detection.box.x,
            y: best.detection.box.y,
            width: best.detection.box.width,
            height: best.detection.box.height,
          };
          this.smoothedBox = this.smoothedBox
            ? this.lerpBox(this.smoothedBox, nextBox, this.boxLerp)
            : nextBox;

          const pose = this.estimatePose(best.landmarks);
          const step = this.currentAngle;
          const poseOk = step ? this.matchesAngle(step.id, pose) : false;
          const label = step ? (poseOk ? `${step.label} ✓` : step.label) : 'ครบ 5 มุม';
          this.drawSmoothOverlay(ctx, this.smoothedBox, label, poseOk, this.capturingAngle);

          this.ngZone.run(() => {
            this.isFaceDetected = true;
            this.checkMatch = true;
            if (step && !step.captured && poseOk && !this.capturingAngle && !this.allAnglesCaptured) {
              if (!this.poseHoldStartedAt) {
                this.poseHoldStartedAt = Date.now();
              } else if (Date.now() - this.poseHoldStartedAt >= this.poseHoldMs) {
                this.captureCurrentAngle();
              } else {
                const left = Math.ceil((this.poseHoldMs - (Date.now() - this.poseHoldStartedAt)) / 100);
                this.faceStatus = `มุม ${this.currentAngleIndex + 1}/5 — ค้างท่าไว้… ${(left / 10).toFixed(1)}s`;
              }
            } else {
              this.poseHoldStartedAt = 0;
              if (step && !step.captured) {
                this.faceStatus = `มุม ${this.currentAngleIndex + 1}/5 — ${step.hint}`;
              } else if (this.allAnglesCaptured) {
                this.faceStatus = 'ครบ 5 มุมแล้ว กดบันทึกเพื่ออัปโหลด';
              }
            }
            this.cdr.detectChanges();
          });
        } else {
          this.smoothedBox = null;
          this.poseHoldStartedAt = 0;
          this.ngZone.run(() => {
            this.isFaceDetected = false;
            this.checkMatch = false;
            const step = this.currentAngle;
            this.faceStatus = step
              ? `มุม ${this.currentAngleIndex + 1}/5 — ไม่พบใบหน้า`
              : 'ครบ 5 มุมแล้ว กดบันทึกเพื่ออัปโหลด';
            this.cdr.detectChanges();
          });
        }
      } catch (e) {
        console.error('detectFace error', e);
      }
    }, 120);
  }

  captureImage(): void {
    if (this.isUploadingFace || this.capturingAngle) {
      return;
    }
    if (this.allAnglesCaptured) {
      void this.uploadAllAngles();
      return;
    }
    if (!this.isFaceDetected) {
      return;
    }
    this.captureCurrentAngle();
  }

  private captureCurrentAngle(): void {
    const step = this.currentAngle;
    if (!step || step.captured || this.capturingAngle || !this.video?.nativeElement) {
      return;
    }
    this.capturingAngle = true;
    this.poseHoldStartedAt = 0;

    const video = this.video.nativeElement;
    const captureCanvas = document.createElement('canvas');
    captureCanvas.width = video.videoWidth || video.width || 640;
    captureCanvas.height = video.videoHeight || video.height || 480;
    const context = captureCanvas.getContext('2d');
    if (!context) {
      this.capturingAngle = false;
      return;
    }
    context.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
    step.preview = captureCanvas.toDataURL('image/jpeg', 0.92);
    step.captured = true;
    this.capturedImage = step.preview;
    playCaptureBeep();

    if (this.currentAngleIndex < this.faceAngleSteps.length - 1) {
      this.currentAngleIndex += 1;
      this.faceStatus = `บันทึกมุม「${step.label}」แล้ว — ${this.currentAngle!.hint}`;
    } else {
      this.faceStatus = 'ครบ 5 มุมแล้ว กดบันทึกเพื่ออัปโหลด';
    }
    this.capturingAngle = false;
    this.cdr.detectChanges();
  }

  async uploadAllAngles(): Promise<void> {
    const pending = this.faceAngleSteps.filter((s) => s.captured && s.preview);
    if (pending.length < 5) {
      swal('ยังไม่ครบ', `ต้องถ่ายครบ 5 มุม (ตอนนี้ ${pending.length}/5)`, 'info');
      return;
    }

    this.isUploadingFace = true;
    try {
      for (let i = 0; i < pending.length; i++) {
        const step = pending[i];
        this.uploadProgressLabel = `กำลังอัปโหลด ${i + 1}/5 (${step.label})...`;
        this.faceStatus = this.uploadProgressLabel;
        this.cdr.detectChanges();
        const file = this.dataURLtoFile(step.preview!, `face-${step.id}.jpg`);
        const formData = new FormData();
        formData.append('file', file);
        await this.http
          .post(environment.baseUrl + `/face/members/${this.memberId}/add-face`, formData)
          .toPromise();
      }
      this.uploadStatus = 'Face uploaded successfully!';
      this.faceStatus = 'บันทึกใบหน้า 5 มุมสำเร็จ';
      swal('Save Success!!', 'บันทึกใบหน้า 5 มุมสำเร็จ', 'success');
    } catch (error: any) {
      this.uploadStatus = 'Error uploading face!';
      const detail = error?.error?.detail || 'บันทึกใบหน้าไม่สำเร็จ';
      this.faceStatus = detail;
      console.error('Error:', error);
      swal('Upload Failed', detail, 'error');
    } finally {
      this.isUploadingFace = false;
      this.uploadProgressLabel = '';
      this.cdr.detectChanges();
    }
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

  private estimatePose(landmarks: faceapi.FaceLandmarks68): { yaw: number; pitch: number } {
    const positions = landmarks.positions;
    const avg = (from: number, to: number) => {
      let x = 0;
      let y = 0;
      const n = to - from + 1;
      for (let i = from; i <= to; i++) {
        x += positions[i].x;
        y += positions[i].y;
      }
      return { x: x / n, y: y / n };
    };
    const leftEye = avg(36, 41);
    const rightEye = avg(42, 47);
    const nose = positions[30];
    const eyeMid = { x: (leftEye.x + rightEye.x) / 2, y: (leftEye.y + rightEye.y) / 2 };
    const eyeDist = Math.max(1, Math.hypot(rightEye.x - leftEye.x, rightEye.y - leftEye.y));
    const yaw = (nose.x - eyeMid.x) / eyeDist;
    const pitch = (nose.y - eyeMid.y) / eyeDist - 0.45;
    return { yaw, pitch };
  }

  private matchesAngle(
    id: FaceAngleStep['id'],
    pose: { yaw: number; pitch: number },
  ): boolean {
    const { yaw, pitch } = pose;
    switch (id) {
      case 'front':
        return Math.abs(yaw) < 0.14 && Math.abs(pitch) < 0.14;
      case 'left':
        // Non-mirrored camera: user turns left → nose toward image-right
        return yaw > 0.22 && Math.abs(pitch) < 0.22;
      case 'right':
        return yaw < -0.22 && Math.abs(pitch) < 0.22;
      case 'up':
        return pitch < -0.16 && Math.abs(yaw) < 0.22;
      case 'down':
        return pitch > 0.18 && Math.abs(yaw) < 0.22;
      default:
        return false;
    }
  }

  private lerpBox(prev: SmoothBox, next: SmoothBox, t: number): SmoothBox {
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
    ready: boolean,
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
    if (ready && !busy) {
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
      ctx.font = '600 15px "Segoe UI", system-ui, sans-serif';
      const metrics = ctx.measureText(label);
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
      ctx.fillText(label, labelX + labelPadX, labelY + labelH / 2 + 1);
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
}
