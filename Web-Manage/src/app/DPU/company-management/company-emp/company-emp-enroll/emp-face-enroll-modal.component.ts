import { CommonModule } from '@angular/common';
import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  NgZone,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { SharedModule } from '../../../../shared/shared.module';
import { playCaptureBeep, unlockBeepAudio } from '../../../../shared/utils/beep';
import { unlockSpeech } from '../../../../shared/utils/tts';
import { TtsSettings, resolveTtsSettings } from '../../../../shared/utils/tts-templates';
import { EmployeeModel } from '../../../models/employee.model';
import { SystemSettingService } from '../../../services/system-setting.service';
import { SmoothBox } from '../company-emp.helpers';
import {
  BrowserFaceDetector,
  createBrowserFaceDetector,
  detectBrowserFaceBox,
  detectServerFaceBox,
  drawSmoothOverlay,
  openUserCamera,
  smoothFaceBox,
  stopMediaStream,
} from './emp-face-enroll.camera';
import { speakEnroll } from './emp-face-enroll.tts';
import {
  FaceAngleStep,
  FaceUploadItem,
  appendFaceUploadFiles,
  clearUploadFaceItems,
  createDefaultFaceAngleSteps,
  uploadAnglePreviews,
  uploadFaceFiles,
} from './emp-face-enroll.upload';
import swal from 'sweetalert';

@Component({
  selector: 'app-emp-face-enroll-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule],
  templateUrl: './emp-face-enroll-modal.component.html',
})
export class EmpFaceEnrollModalComponent implements OnDestroy {
  @ViewChild('closeModalFace') public childModalFace?: ElementRef;
  @ViewChild('video') video?: ElementRef;
  @ViewChild('canvas') canvas?: ElementRef;
  @ViewChild('faceUploadInput') faceUploadInput?: ElementRef<HTMLInputElement>;

  @Input() companyId = '';
  @Input() selectModel: EmployeeModel = new EmployeeModel();

  faceStatus = 'เปิดกล้องเพื่อสแกนใบหน้า';
  isUploadingFace = false;
  isFaceDetected = false;
  checkMatch = false;
  faceEnrollMode: 'camera' | 'upload' = 'camera';
  faceAngleSteps: FaceAngleStep[] = [];
  currentAngleIndex = 0;
  uploadFaceItems: FaceUploadItem[] = [];
  uploadProgressLabel = '';
  capturedImage: string | null = null;
  uploadStatus = '';

  private ttsSettings: TtsSettings = resolveTtsSettings(null);
  private faceDetector: BrowserFaceDetector | null = null;
  private faceDetectionInterval: ReturnType<typeof setInterval> | null = null;
  private useServerFaceDetect = false;
  private serverDetectInFlight = false;
  private lastServerDetectAt = 0;
  private enrollDetectCanvas: HTMLCanvasElement | null = null;
  private videoStream: MediaStream | null = null;
  private smoothedBox: SmoothBox | null = null;
  private poseHoldStartedAt = 0;
  private captureCooldownUntil = 0;
  private faceDetectBusy = false;
  private capturingAngle = false;
  private modelsLoaded = false;
  private readonly boxLerp = 0.35;
  private readonly poseHoldMs = 450;
  private readonly captureCooldownMs = 850;

  constructor(
    private http: HttpClient,
    private systemSettingService: SystemSettingService,
    private ngZone: NgZone,
    private cdr: ChangeDetectorRef,
  ) {
    this.loadTtsSettings();
  }

  get currentAngle(): FaceAngleStep | null {
    return this.faceAngleSteps[this.currentAngleIndex] || null;
  }

  get capturedAngleCount(): number {
    return this.faceAngleSteps.filter((s) => s.captured).length;
  }

  get allAnglesCaptured(): boolean {
    return this.faceAngleSteps.length > 0 && this.capturedAngleCount === this.faceAngleSteps.length;
  }

  ngOnDestroy(): void {
    this.closeFaceEnrollModal();
  }

  async openForEmployee(item: EmployeeModel): Promise<void> {
    this.selectModel = item;
    this.resetFaceAngles();
    this.clearUploads();
    this.faceEnrollMode = 'camera';
    this.checkMatch = false;
    this.isFaceDetected = false;
    this.capturingAngle = false;
    this.smoothedBox = null;
    this.poseHoldStartedAt = 0;
    this.captureCooldownUntil = 0;
    this.faceDetectBusy = false;
    this.uploadProgressLabel = '';
    this.faceStatus = 'กำลังโหลดโมเดลและกล้อง...';
    this.cdr.detectChanges();
    await this.startCameraEnroll();
  }

  async setFaceEnrollMode(mode: 'camera' | 'upload'): Promise<void> {
    if (this.isUploadingFace || this.faceEnrollMode === mode) return;
    this.faceEnrollMode = mode;
    if (mode === 'upload') {
      this.stopFaceCamera();
      this.faceStatus = 'เลือกไฟล์รูปใบหน้าเพื่อลงทะเบียน';
      this.cdr.detectChanges();
      return;
    }
    this.faceStatus = 'กำลังโหลดโมเดลและกล้อง...';
    this.cdr.detectChanges();
    await this.startCameraEnroll();
  }

  triggerFaceUploadPicker(): void {
    if (this.isUploadingFace) return;
    if (this.faceUploadInput?.nativeElement) {
      this.faceUploadInput.nativeElement.value = '';
      this.faceUploadInput.nativeElement.click();
    }
  }

  onFaceUploadSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files || []);
    input.value = '';
    if (!files.length) return;
    const { items, rejected } = appendFaceUploadFiles(this.uploadFaceItems, files);
    this.uploadFaceItems = items;
    if (rejected.length) {
      swal('ไฟล์ไม่ถูกต้อง', `รองรับเฉพาะ JPG / PNG / WEBP\n(${rejected.join(', ')})`, 'warning');
    }
    this.faceStatus =
      this.uploadFaceItems.length > 0
        ? `เลือกแล้ว ${this.uploadFaceItems.length} รูป — กดบันทึกเพื่อลงทะเบียน`
        : 'เลือกไฟล์รูปใบหน้าเพื่อลงทะเบียน';
    this.cdr.detectChanges();
  }

  removeUploadFaceItem(index: number): void {
    const item = this.uploadFaceItems[index];
    if (item?.preview) URL.revokeObjectURL(item.preview);
    this.uploadFaceItems.splice(index, 1);
    this.faceStatus =
      this.uploadFaceItems.length > 0
        ? `เลือกแล้ว ${this.uploadFaceItems.length} รูป — กดบันทึกเพื่อลงทะเบียน`
        : 'เลือกไฟล์รูปใบหน้าเพื่อลงทะเบียน';
    this.cdr.detectChanges();
  }

  closeFaceEnrollModal(): void {
    this.stopFaceCamera();
    this.clearUploads();
    this.isUploadingFace = false;
    this.uploadProgressLabel = '';
  }

  captureImage(): void {
    if (this.isUploadingFace || this.capturingAngle) return;
    if (this.faceEnrollMode === 'upload') {
      void this.uploadFacePhotos();
      return;
    }
    if (!this.selectModel?.member?.memberId) {
      swal('Error', 'ไม่พบข้อมูลพนักงาน', 'error');
      return;
    }
    if (this.allAnglesCaptured) {
      void this.uploadAllAngles();
      return;
    }
    if (!this.isFaceDetected) {
      swal('ยังไม่พร้อม', 'กรุณาวางใบหน้าให้อยู่ในกรอบก่อน', 'info');
      return;
    }
    this.captureCurrentAngle();
  }

  private loadTtsSettings(): void {
    this.systemSettingService.getTtsSettings().subscribe({
      next: (settings) => (this.ttsSettings = settings),
      error: () => undefined,
    });
  }

  private clearUploads(): void {
    clearUploadFaceItems(this.uploadFaceItems);
    this.uploadFaceItems = [];
  }

  private resetFaceAngles(): void {
    this.currentAngleIndex = 0;
    this.faceAngleSteps = createDefaultFaceAngleSteps();
  }

  private async startCameraEnroll(): Promise<void> {
    try {
      unlockBeepAudio();
      unlockSpeech();
      await this.ensureFaceModels();
      await this.startVideo();
      this.updateAngleStatus();
      this.cdr.detectChanges();
      setTimeout(() => this.detectFace(), 300);
    } catch (err: any) {
      console.error(err);
      this.faceStatus = err?.message || 'เปิดกล้องไม่สำเร็จ';
      this.cdr.detectChanges();
    }
  }

  private async ensureFaceModels(): Promise<void> {
    if (this.modelsLoaded) return;
    this.faceDetector = createBrowserFaceDetector();
    this.useServerFaceDetect = !this.faceDetector;
    this.modelsLoaded = true;
    if (this.useServerFaceDetect) {
      this.faceStatus = 'ใช้ตรวจจับใบหน้าจากเซิร์ฟเวอร์ (เบราว์เซอร์ไม่รองรับ FaceDetector)';
      this.cdr.detectChanges();
    }
  }

  private async startVideo(): Promise<void> {
    this.stopFaceCamera();
    const stream = await openUserCamera();
    this.videoStream = stream;
    if (this.video?.nativeElement) {
      this.video.nativeElement.srcObject = stream;
    }
  }

  stopFaceCamera(): void {
    if (this.faceDetectionInterval) {
      clearInterval(this.faceDetectionInterval);
      this.faceDetectionInterval = null;
    }
    stopMediaStream(this.videoStream, this.video?.nativeElement);
    this.videoStream = null;
    this.smoothedBox = null;
  }

  private updateAngleStatus(): void {
    const step = this.currentAngle;
    if (!step) {
      this.faceStatus = 'ครบ 5 มุมแล้ว กดบันทึกเพื่ออัปโหลด';
      this.checkMatch = true;
      return;
    }
    this.faceStatus = `มุม ${this.currentAngleIndex + 1}/5 — ${step.hint}`;
    this.checkMatch = this.isFaceDetected;
  }

  async detectFace(): Promise<void> {
    if (!this.video?.nativeElement || !this.canvas?.nativeElement) return;
    const videoEl = this.video.nativeElement;
    const displaySize = {
      width: videoEl.clientWidth || videoEl.width || 640,
      height: videoEl.clientHeight || videoEl.height || 480,
    };
    this.canvas.nativeElement.width = displaySize.width;
    this.canvas.nativeElement.height = displaySize.height;
    if (this.faceDetectionInterval) clearInterval(this.faceDetectionInterval);

    this.faceDetectionInterval = setInterval(async () => {
      if (
        !videoEl.srcObject ||
        videoEl.readyState < 2 ||
        this.isUploadingFace ||
        this.faceDetectBusy ||
        this.faceEnrollMode !== 'camera'
      ) {
        return;
      }
      this.faceDetectBusy = true;
      try {
        const liveSize = {
          width: videoEl.clientWidth || videoEl.width || 640,
          height: videoEl.clientHeight || videoEl.height || 480,
        };
        if (
          this.canvas!.nativeElement.width !== liveSize.width ||
          this.canvas!.nativeElement.height !== liveSize.height
        ) {
          this.canvas!.nativeElement.width = liveSize.width;
          this.canvas!.nativeElement.height = liveSize.height;
        }

        let nextBox = await detectBrowserFaceBox(this.faceDetector, videoEl, liveSize);
        if (!nextBox && this.useServerFaceDetect) {
          const now = Date.now();
          if (!this.serverDetectInFlight && now - this.lastServerDetectAt >= 280) {
            this.serverDetectInFlight = true;
            this.lastServerDetectAt = now;
            try {
              if (!this.enrollDetectCanvas) {
                this.enrollDetectCanvas = document.createElement('canvas');
              }
              nextBox = await detectServerFaceBox(
                this.http,
                videoEl,
                liveSize,
                this.enrollDetectCanvas,
              );
            } finally {
              this.serverDetectInFlight = false;
            }
          } else {
            nextBox = this.smoothedBox;
          }
        }

        const ctx = this.canvas!.nativeElement.getContext('2d') as CanvasRenderingContext2D;
        ctx.clearRect(0, 0, liveSize.width, liveSize.height);

        if (nextBox) {
          this.smoothedBox = smoothFaceBox(this.smoothedBox, nextBox, this.boxLerp);
          const step = this.currentAngle;
          const inCooldown = Date.now() < this.captureCooldownUntil;
          const ready = !!step && !inCooldown;
          const label = step ? (ready ? `${step.label} ✓` : step.label) : 'ครบ 5 มุม';
          drawSmoothOverlay(ctx, this.smoothedBox, label, ready, this.capturingAngle);

          this.ngZone.run(() => {
            this.isFaceDetected = true;
            this.checkMatch = true;
            if (step && !step.captured && !this.capturingAngle && !this.allAnglesCaptured && !inCooldown) {
              if (!this.poseHoldStartedAt) {
                this.poseHoldStartedAt = Date.now();
              } else if (Date.now() - this.poseHoldStartedAt >= this.poseHoldMs) {
                this.captureCurrentAngle();
              } else {
                const leftSec = Math.max(
                  0,
                  (this.poseHoldMs - (Date.now() - this.poseHoldStartedAt)) / 1000,
                );
                this.faceStatus = `มุม ${this.currentAngleIndex + 1}/5 — ${step.hint} ค้างไว้… ${leftSec.toFixed(1)}s`;
              }
            } else if (step && !step.captured) {
              this.faceStatus = `มุม ${this.currentAngleIndex + 1}/5 — ${step.hint}`;
            } else if (this.allAnglesCaptured) {
              this.faceStatus = 'ครบ 5 มุมแล้ว กดบันทึกเพื่ออัปโหลด';
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
      } finally {
        this.faceDetectBusy = false;
      }
    }, 160);
  }

  private captureCurrentAngle(): void {
    const step = this.currentAngle;
    if (!step || step.captured || this.capturingAngle || !this.video?.nativeElement) return;
    this.capturingAngle = true;
    this.poseHoldStartedAt = 0;
    const video = this.video.nativeElement;
    const captureCanvas = document.createElement('canvas');
    captureCanvas.width = video.videoWidth || video.width || 640;
    captureCanvas.height = video.videoHeight || video.height || 480;
    const context = captureCanvas.getContext('2d');
    if (!context) {
      this.capturingAngle = false;
      swal('Error', 'ไม่สามารถจับภาพจากกล้องได้', 'error');
      return;
    }
    context.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
    step.preview = captureCanvas.toDataURL('image/jpeg', 0.92);
    step.captured = true;
    this.capturedImage = step.preview;
    this.captureCooldownUntil = Date.now() + this.captureCooldownMs;
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

  async uploadFacePhotos(): Promise<void> {
    if (!this.selectModel?.member?.memberId) {
      swal('Error', 'ไม่พบข้อมูลพนักงาน', 'error');
      return;
    }
    if (!this.uploadFaceItems.length) {
      swal('ยังไม่มีรูป', 'กรุณาเลือกรูปใบหน้าอย่างน้อย 1 รูป', 'info');
      return;
    }
    this.isUploadingFace = true;
    const memberId = this.selectModel.member.memberId;
    try {
      await uploadFaceFiles(
        this.http,
        this.companyId,
        memberId,
        this.uploadFaceItems.map((i) => i.file),
        (label) => {
          this.uploadProgressLabel = label;
          this.faceStatus = label;
          this.cdr.detectChanges();
        },
      );
      this.uploadStatus = 'Face uploaded successfully!';
      this.faceStatus = `บันทึกใบหน้า ${this.uploadFaceItems.length} รูปสำเร็จ`;
      speakEnroll(this.ttsSettings, this.selectModel, true);
      swal('Save Success!!', `บันทึกใบหน้า ${this.uploadFaceItems.length} รูปสำเร็จ`, 'success');
      this.clearUploads();
      this.childModalFace?.nativeElement.click();
      this.stopFaceCamera();
    } catch (error: any) {
      const detail = error?.error?.detail || 'บันทึกใบหน้าไม่สำเร็จ';
      this.uploadStatus = 'Error uploading face!';
      this.faceStatus = detail;
      speakEnroll(this.ttsSettings, this.selectModel, false);
      swal('Upload Failed', detail, 'error');
    } finally {
      this.isUploadingFace = false;
      this.uploadProgressLabel = '';
      this.cdr.detectChanges();
    }
  }

  async uploadAllAngles(): Promise<void> {
    if (!this.selectModel?.member?.memberId) {
      swal('Error', 'ไม่พบข้อมูลพนักงาน', 'error');
      return;
    }
    const pending = this.faceAngleSteps.filter((s) => s.captured && s.preview);
    if (pending.length < 5) {
      swal('ยังไม่ครบ', `ต้องถ่ายครบ 5 มุม (ตอนนี้ ${pending.length}/5)`, 'info');
      return;
    }
    this.isUploadingFace = true;
    const memberId = this.selectModel.member.memberId;
    try {
      await uploadAnglePreviews(this.http, this.companyId, memberId, this.faceAngleSteps, (label) => {
        this.uploadProgressLabel = label;
        this.faceStatus = label;
        this.cdr.detectChanges();
      });
      this.uploadStatus = 'Face uploaded successfully!';
      this.faceStatus = 'บันทึกใบหน้า 5 มุมสำเร็จ';
      speakEnroll(this.ttsSettings, this.selectModel, true);
      swal('Save Success!!', 'บันทึกใบหน้า 5 มุมสำเร็จ', 'success');
      this.childModalFace?.nativeElement.click();
      this.stopFaceCamera();
    } catch (error: any) {
      const detail = error?.error?.detail || 'บันทึกใบหน้าไม่สำเร็จ';
      this.uploadStatus = 'Error uploading face!';
      this.faceStatus = detail;
      speakEnroll(this.ttsSettings, this.selectModel, false);
      swal('Upload Failed', detail, 'error');
    } finally {
      this.isUploadingFace = false;
      this.uploadProgressLabel = '';
      this.cdr.detectChanges();
    }
  }
}
