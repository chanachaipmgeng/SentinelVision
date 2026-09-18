import { CommonModule } from "@angular/common";
import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, NgZone, OnDestroy, ViewChild } from '@angular/core';
import { MaterialModuleModule } from "../../../material-module/material-module.module";
import { RouterModule } from "@angular/router";
import { NgSelectModule } from "@ng-select/ng-select";
import { SharedModule } from "../../../shared/shared.module";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { FlatpickrDefaults, FlatpickrModule } from "angularx-flatpickr";
import { MatDatepickerModule } from "@angular/material/datepicker";
import { EmployeeModel } from "../../models/employee.model";
import { EmployeeService } from "../../services/employee.service";
import { TokenService } from "../../../shared/services/token.service";
import swal from 'sweetalert';
import { DepartmentService } from "../../services/department.service";
import { PositionService } from "../../services/position.service";
import { DepartmentModel } from "../../models/department.model";
import { PositionModel } from "../../models/position.model";
import { FormsModule } from "@angular/forms";
import { FileUploadModule } from 'ng2-file-upload';
import { FileItem, FileUploader, ParsedResponseHeaders } from "ng2-file-upload";
import { environment } from "../../../../environments/environment";
import { HttpClient } from "@angular/common/http";
import { FaceManagementComponent } from '../dialogs/face-management/face-management.component';
import { firstValueFrom } from 'rxjs';
import { playCaptureBeep, unlockBeepAudio } from '../../../shared/utils/beep';
import { speakText, unlockSpeech } from '../../../shared/utils/tts';
import {
  TtsSettings,
  buildSpeechText,
  resolveTtsSettings,
} from '../../../shared/utils/tts-templates';
import { SystemSettingService } from '../../services/system-setting.service';

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
  selector: 'app-company-emp',
  standalone: true,
  imports: [SharedModule, NgSelectModule, RouterModule, MaterialModuleModule, TranslateModule, FlatpickrModule, MatDatepickerModule, FormsModule, CommonModule, FileUploadModule, FaceManagementComponent],
  providers: [FlatpickrDefaults],
  templateUrl: './company-emp.component.html',
  styleUrl: './company-emp.component.css',
})
export class CompanyEmpComponent implements OnDestroy, AfterViewInit {
  @ViewChild('closeModal') public childModal?: ElementRef;
  @ViewChild('closeModalFace') public childModalFace?: ElementRef;
  @ViewChild('modalDetail') public modalDetail?: ElementRef;
  allSelected = false;
  someSelected = false;
  uploaderProfile: FileUploader | undefined;
  uploadErrorMsg: string = "";
  itemsList: EmployeeModel[] = []
  /** Full search result set (before paging). */
  filteredSource: EmployeeModel[] = []
  /** Current page slice shown in table/cards. */
  filterList: EmployeeModel[] = []
  selectModel: EmployeeModel = new EmployeeModel()
  selectedItems = new Map<string, boolean>();
  departmentList: DepartmentModel[] = []
  positionList: PositionModel[] = []
  pageIndex = 0;
  /** Table: 10/page · Cards: 9/page (3×3 grid). */
  pageSize = 10;
  private readonly tablePageSize = 10;
  private readonly cardsPageSize = 9;
  /** Exclusive list layout — only one view shown at a time. */
  listViewMode: 'table' | 'cards' = 'cards';
  private readonly listViewStorageKey = 'dpu.companyEmp.listView';
  public selectedMemberId: string | null = null;
  public selectedMemberName = '';
  get searchTerm(): string {
    return this._searchTerm;
  }
  set searchTerm(val: string) {
    this.pageIndex = 0;
    this.allSelected = false;
    this._searchTerm = val ?? '';
    this.applyFilter();
  }

  get totalFiltered(): number {
    return this.filteredSource.length;
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.totalFiltered / this.pageSize) || 1);
  }

  get pageStart(): number {
    return this.totalFiltered === 0 ? 0 : this.pageIndex * this.pageSize + 1;
  }

  get pageEnd(): number {
    return Math.min((this.pageIndex + 1) * this.pageSize, this.totalFiltered);
  }
  companyId = ""
  _searchTerm = "";
  isEdit = false;
  isImporting = false;
  @ViewChild('importFileInput') importFileInput?: ElementRef<HTMLInputElement>;
  @ViewChild('importPhotosInput') importPhotosInput?: ElementRef<HTMLInputElement>;
  private pendingImportExcel: File | null = null;
  private ttsSettings: TtsSettings = resolveTtsSettings(null);

  constructor(
    private http: HttpClient,
    private employeeService: EmployeeService,
    public translate: TranslateService,
    private departmentService: DepartmentService,
    private positionService: PositionService,
    private systemSettingService: SystemSettingService,
    private tokenService: TokenService,
    private ngZone: NgZone,
    private cdr: ChangeDetectorRef,
  ) {
    this.uploadConfig()
    this.companyId = this.tokenService.getSelectCompany().companyId;
  }

  @ViewChild('video') video: ElementRef;
  @ViewChild('canvas') canvas: ElementRef;
  capturedImage: string | null = null;
  uploadStatus: string = '';
  checkMatch = false;
  faceStatus = 'เปิดกล้องเพื่อสแกนใบหน้า';
  isUploadingFace = false;
  memberId = ""
  isFaceDetected = false;
  faceAngleSteps: FaceAngleStep[] = [];
  currentAngleIndex = 0;
  uploadProgressLabel = '';
  faceEnrollMode: 'camera' | 'upload' = 'camera';
  uploadFaceItems: { file: File; preview: string }[] = [];
  @ViewChild('faceUploadInput') faceUploadInput?: ElementRef<HTMLInputElement>;
  private modelsLoaded = false;
  /** Browser FaceDetector (Chrome). Local face-api models are not shipped. */
  private faceDetector: { detect: (source: HTMLVideoElement) => Promise<Array<{ boundingBox: { x: number; y: number; width: number; height: number } }>> } | null = null;
  private faceDetectionInterval: ReturnType<typeof setInterval> | null = null;
  private videoStream: MediaStream | null = null;
  private smoothedBox: SmoothBox | null = null;
  private poseHoldStartedAt = 0;
  private poseMissStartedAt = 0;
  private captureCooldownUntil = 0;
  private faceDetectBusy = false;
  private capturingAngle = false;
  private readonly boxLerp = 0.35;
  private readonly poseHoldMs = 450;
  private readonly poseMissGraceMs = 300;
  private readonly captureCooldownMs = 850;
  private readonly bodyModalIds = ['modal-face', 'modal-detail', 'modal-face-management'];
  private movedModalNodes: HTMLElement[] = [];

  get currentAngle(): FaceAngleStep | null {
    return this.faceAngleSteps[this.currentAngleIndex] || null;
  }

  get capturedAngleCount(): number {
    return this.faceAngleSteps.filter((s) => s.captured).length;
  }

  get allAnglesCaptured(): boolean {
    return this.faceAngleSteps.length > 0 && this.capturedAngleCount === this.faceAngleSteps.length;
  }

  ngAfterViewInit(): void {
    // Preline backdrop is on <body>; keep overlays there too so content is never under it.
    this.bodyModalIds.forEach((id) => {
      const el = document.getElementById(id);
      if (el && el.parentElement !== document.body) {
        document.body.appendChild(el);
        this.movedModalNodes.push(el);
      }
    });
  }

  ngOnDestroy(): void {
    this.closeFaceEnrollModal();
    this.movedModalNodes.forEach((el) => el.remove());
    this.movedModalNodes = [];
  }

  async openFaceEnroll(item: EmployeeModel): Promise<void> {
    this.view(item);
    this.resetFaceAngles();
    this.clearUploadFaceItems();
    this.faceEnrollMode = 'camera';
    this.checkMatch = false;
    this.isFaceDetected = false;
    this.capturingAngle = false;
    this.smoothedBox = null;
    this.poseHoldStartedAt = 0;
    this.poseMissStartedAt = 0;
    this.captureCooldownUntil = 0;
    this.faceDetectBusy = false;
    this.uploadProgressLabel = '';
    this.faceStatus = 'กำลังโหลดโมเดลและกล้อง...';
    this.cdr.detectChanges();
    await this.startCameraEnroll();
  }

  async setFaceEnrollMode(mode: 'camera' | 'upload'): Promise<void> {
    if (this.isUploadingFace || this.faceEnrollMode === mode) {
      return;
    }
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

  private loadTtsSettings(): void {
    this.systemSettingService.getTtsSettings().subscribe({
      next: (settings) => {
        this.ttsSettings = settings;
      },
      error: () => {
        /* keep defaults */
      },
    });
  }

  private enrollSpeechVars(): { name: string; firstName: string; employeeId: string } {
    const member = this.selectModel?.member;
    const name =
      (typeof this.selectModel?.getFullname === 'function'
        ? this.selectModel.getFullname()
        : ''
      )?.trim() ||
      `${member?.firstName || ''} ${member?.lastName || ''}`.trim() ||
      'พนักงาน';
    return {
      name,
      firstName: (member?.firstName || name.split(/\s+/)[0] || '').trim(),
      employeeId: this.selectModel?.employeeId || '',
    };
  }

  private speakEnroll(success: boolean): void {
    const text = buildSpeechText(
      this.ttsSettings,
      success ? 'enrollSuccess' : 'enrollFailed',
      this.enrollSpeechVars(),
    );
    if (!text) return;
    speakText(text, {
      lang: this.ttsSettings.lang,
      rate: this.ttsSettings.rate,
      pitch: this.ttsSettings.pitch,
      cancelPrevious: true,
    });
  }

  triggerFaceUploadPicker(): void {
    if (this.isUploadingFace) {
      return;
    }
    if (this.faceUploadInput?.nativeElement) {
      this.faceUploadInput.nativeElement.value = '';
      this.faceUploadInput.nativeElement.click();
    }
  }

  onFaceUploadSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files || []);
    input.value = '';
    if (!files.length) {
      return;
    }
    const allowed = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
    for (const file of files) {
      const okType =
        allowed.includes((file.type || '').toLowerCase()) ||
        /\.(jpe?g|png|webp)$/i.test(file.name || '');
      if (!okType) {
        swal('ไฟล์ไม่ถูกต้อง', `รองรับเฉพาะ JPG / PNG / WEBP\n(${file.name})`, 'warning');
        continue;
      }
      this.uploadFaceItems.push({
        file,
        preview: URL.createObjectURL(file),
      });
    }
    this.faceStatus =
      this.uploadFaceItems.length > 0
        ? `เลือกแล้ว ${this.uploadFaceItems.length} รูป — กดบันทึกเพื่อลงทะเบียน`
        : 'เลือกไฟล์รูปใบหน้าเพื่อลงทะเบียน';
    this.cdr.detectChanges();
  }

  removeUploadFaceItem(index: number): void {
    const item = this.uploadFaceItems[index];
    if (item?.preview) {
      URL.revokeObjectURL(item.preview);
    }
    this.uploadFaceItems.splice(index, 1);
    this.faceStatus =
      this.uploadFaceItems.length > 0
        ? `เลือกแล้ว ${this.uploadFaceItems.length} รูป — กดบันทึกเพื่อลงทะเบียน`
        : 'เลือกไฟล์รูปใบหน้าเพื่อลงทะเบียน';
    this.cdr.detectChanges();
  }

  private clearUploadFaceItems(): void {
    this.uploadFaceItems.forEach((item) => {
      if (item.preview) {
        URL.revokeObjectURL(item.preview);
      }
    });
    this.uploadFaceItems = [];
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
      for (let i = 0; i < this.uploadFaceItems.length; i++) {
        const item = this.uploadFaceItems[i];
        this.uploadProgressLabel = `กำลังอัปโหลด ${i + 1}/${this.uploadFaceItems.length}...`;
        this.faceStatus = this.uploadProgressLabel;
        this.cdr.detectChanges();
        const formData = new FormData();
        formData.append('file', item.file, item.file.name || `face-${i + 1}.jpg`);
        await firstValueFrom(
          this.http.post(environment.baseUrl + `/face/members/${memberId}/add-face`, formData),
        );
      }
      this.uploadStatus = 'Face uploaded successfully!';
      this.faceStatus = `บันทึกใบหน้า ${this.uploadFaceItems.length} รูปสำเร็จ`;
      this.cdr.detectChanges();
      this.speakEnroll(true);
      swal('Save Success!!', `บันทึกใบหน้า ${this.uploadFaceItems.length} รูปสำเร็จ`, 'success');
      this.clearUploadFaceItems();
      this.childModalFace?.nativeElement.click();
      this.stopFaceCamera();
    } catch (error: any) {
      const detail = error?.error?.detail || 'บันทึกใบหน้าไม่สำเร็จ';
      this.uploadStatus = 'Error uploading face!';
      this.faceStatus = detail;
      this.cdr.detectChanges();
      console.error('Error:', error);
      this.speakEnroll(false);
      swal('Upload Failed', detail, 'error');
    } finally {
      this.isUploadingFace = false;
      this.uploadProgressLabel = '';
      this.cdr.detectChanges();
    }
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

  private async ensureFaceModels(): Promise<void> {
    if (this.modelsLoaded) {
      return;
    }
    const FaceDetectorCtor = (globalThis as { FaceDetector?: new (opts?: object) => NonNullable<CompanyEmpComponent['faceDetector']> }).FaceDetector;
    if (typeof FaceDetectorCtor === 'function') {
      try {
        this.faceDetector = new FaceDetectorCtor({ fastMode: true, maxDetectedFaces: 1 });
      } catch {
        this.faceDetector = null;
      }
    }
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
      throw new Error('ไม่สามารถเปิดกล้องได้ กรุณาอนุญาตการใช้กล้องในเบราว์เซอร์');
    });
  }

  stopFaceCamera(): void {
    if (this.faceDetectionInterval) {
      clearInterval(this.faceDetectionInterval);
      this.faceDetectionInterval = null;
    }
    if (this.videoStream) {
      this.videoStream.getTracks().forEach((track) => track.stop());
      this.videoStream = null;
    }
    if (this.video?.nativeElement) {
      this.video.nativeElement.srcObject = null;
    }
    this.smoothedBox = null;
  }

  closeFaceEnrollModal(): void {
    this.stopFaceCamera();
    this.clearUploadFaceItems();
    this.isUploadingFace = false;
    this.uploadProgressLabel = '';
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

    if (this.faceDetectionInterval) {
      clearInterval(this.faceDetectionInterval);
    }

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
          this.canvas.nativeElement.width !== liveSize.width ||
          this.canvas.nativeElement.height !== liveSize.height
        ) {
          this.canvas.nativeElement.width = liveSize.width;
          this.canvas.nativeElement.height = liveSize.height;
        }

        const nextBox = await this.detectBrowserFaceBox(videoEl, liveSize);
        const ctx = this.canvas.nativeElement.getContext('2d') as CanvasRenderingContext2D;
        ctx.clearRect(0, 0, liveSize.width, liveSize.height);

        if (nextBox) {
          this.smoothedBox = this.smoothedBox
            ? this.lerpBox(this.smoothedBox, nextBox, this.boxLerp)
            : nextBox;

          const step = this.currentAngle;
          const inCooldown = Date.now() < this.captureCooldownUntil;
          const ready = !!step && !inCooldown;
          const label = step
            ? (ready ? `${step.label} ✓` : step.label)
            : 'ครบ 5 มุม';

          this.drawSmoothOverlay(ctx, this.smoothedBox, label, ready, this.capturingAngle);

          this.ngZone.run(() => {
            this.isFaceDetected = true;
            this.checkMatch = true;
            if (
              step &&
              !step.captured &&
              !this.capturingAngle &&
              !this.allAnglesCaptured &&
              !inCooldown
            ) {
              this.poseMissStartedAt = 0;
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
          this.poseMissStartedAt = 0;
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

  /** Box in display pixels. Null when the browser has no FaceDetector or no face. */
  private async detectBrowserFaceBox(
    videoEl: HTMLVideoElement,
    liveSize: { width: number; height: number },
  ): Promise<SmoothBox | null> {
    if (!this.faceDetector) {
      return null;
    }
    const faces = await this.faceDetector.detect(videoEl);
    const box = faces[0]?.boundingBox;
    if (!box || box.width < 8 || box.height < 8) {
      return null;
    }
    const sx = liveSize.width / (videoEl.videoWidth || liveSize.width);
    const sy = liveSize.height / (videoEl.videoHeight || liveSize.height);
    return {
      x: box.x * sx,
      y: box.y * sy,
      width: box.width * sx,
      height: box.height * sy,
    };
  }

  captureImage(): void {
    if (this.isUploadingFace || this.capturingAngle) {
      return;
    }
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

  private captureCurrentAngle(): void {
    const step = this.currentAngle;
    if (!step || step.captured || this.capturingAngle || !this.video?.nativeElement) {
      return;
    }
    this.capturingAngle = true;
    this.poseHoldStartedAt = 0;
    this.poseMissStartedAt = 0;

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
      for (let i = 0; i < pending.length; i++) {
        const step = pending[i];
        this.uploadProgressLabel = `กำลังอัปโหลด ${i + 1}/5 (${step.label})...`;
        this.faceStatus = this.uploadProgressLabel;
        this.cdr.detectChanges();
        const file = this.dataURLtoFile(step.preview!, `face-${step.id}.jpg`);
        const formData = new FormData();
        formData.append('file', file);
        await firstValueFrom(
          this.http.post(environment.baseUrl + `/face/members/${memberId}/add-face`, formData),
        );
      }
      this.uploadStatus = 'Face uploaded successfully!';
      this.faceStatus = 'บันทึกใบหน้า 5 มุมสำเร็จ';
      this.cdr.detectChanges();
      this.speakEnroll(true);
      swal('Save Success!!', 'บันทึกใบหน้า 5 มุมสำเร็จ', 'success');
      this.childModalFace?.nativeElement.click();
      this.stopFaceCamera();
    } catch (error: any) {
      const detail = error?.error?.detail || 'บันทึกใบหน้าไม่สำเร็จ';
      this.uploadStatus = 'Error uploading face!';
      this.faceStatus = detail;
      this.cdr.detectChanges();
      console.error('Error:', error);
      this.speakEnroll(false);
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

  uploadConfig() {
    this.uploaderProfile = new FileUploader({
      url: environment.baseUrl + "/api/upload-image",
      isHTML5: true,
      authToken: this.tokenService.getToken()!,
    });

    this.uploaderProfile.onAfterAddingFile = (fileItem: FileItem) => {
      fileItem.withCredentials = false;
      this.uploadErrorMsg = "";

      while (this.uploaderProfile!.queue.length > 1) {
        this.uploaderProfile!.queue[0].remove();
      }

      if (fileItem.file.size > 5000000) {
        this.uploadErrorMsg = "maximum file size 5mb.";
        swal("Opp!!", "ไม่สามารถอัพโหลดได้", "info");
        fileItem.isCancel = true;
        return;
      }

      if (fileItem.file.type!.indexOf("image") === -1) {
        this.uploadErrorMsg = "please upload image only.";
        swal("Opp!!", "ไม่สามารถอัพโหลดได้", "info");
        fileItem.isCancel = true;
        return;
      }

      fileItem.upload();
    };

    this.uploaderProfile.onCompleteItem = (
      item: FileItem,
      response: string,
      status: number,
      headers: ParsedResponseHeaders
    ) => {
      if (item.isSuccess) {
        const res = JSON.parse(response);
        console.log("res", res);
        this.selectModel.member.picture = res.filename
        swal(res.message, "บันทึกสำเร็จ", "success");

      } else {
        this.uploadErrorMsg = "cannot upload file.";
        swal("Opp!!", "ไม่สามารถอัพโหลดได้", "info");
      }
    };
  }

  ngOnInit(): void {
    this.initListViewMode();
    this.loadTtsSettings();
    this.getDepartment()
    this.getPosition()

    this.employeeService.getLists(this.companyId).subscribe(result => {
      this.itemsList = result
      this.applyFilter()
    })
  }

  private initListViewMode(): void {
    try {
      const saved = localStorage.getItem(this.listViewStorageKey);
      if (saved === 'table' || saved === 'cards') {
        this.listViewMode = saved;
        this.syncPageSizeForView();
        return;
      }
    } catch {
      /* ignore */
    }
    this.listViewMode = 'cards';
    this.syncPageSizeForView();
  }

  private syncPageSizeForView(): void {
    this.pageSize =
      this.listViewMode === 'cards' ? this.cardsPageSize : this.tablePageSize;
  }

  setListViewMode(mode: 'table' | 'cards'): void {
    if (this.listViewMode === mode) {
      return;
    }
    this.listViewMode = mode;
    this.syncPageSizeForView();
    this.pageIndex = 0;
    this.updatePagedItems();
    try {
      localStorage.setItem(this.listViewStorageKey, mode);
    } catch {
      /* ignore */
    }
  }

  getDepartment() {
    this.departmentService.getLists(this.companyId).subscribe(result => {
      this.departmentList = result
    })
  }

  getPosition() {
    this.positionService.getLists(this.companyId).subscribe(result => {
      this.positionList = result
    })
  }

  filter(v: string): EmployeeModel[] {
    const q = (v || '').toLowerCase().trim();
    if (!q) {
      return [...this.itemsList];
    }
    return (this.itemsList || []).filter(
      (x) =>
        x.company_employeeId?.toLowerCase().indexOf(q) !== -1 ||
        x.employeeId?.toLowerCase().indexOf(q) !== -1 ||
        x.getFullname()?.toLowerCase().indexOf(q) !== -1 ||
        x.getType()?.toLowerCase().indexOf(q) !== -1 ||
        x.getRole()?.toLowerCase().indexOf(q) !== -1 ||
        x.position?.getName()?.toLowerCase().indexOf(q) !== -1 ||
        x.department?.getName()?.toLowerCase().indexOf(q) !== -1 ||
        x.member?.email?.toLowerCase().indexOf(q) !== -1,
    );
  }

  applyFilter(): void {
    this.filteredSource = this.filter(this._searchTerm);
    if (this.pageIndex >= this.totalPages) {
      this.pageIndex = Math.max(0, this.totalPages - 1);
    }
    this.updatePagedItems();
  }

  goToPage(index: number): void {
    if (index < 0 || index >= this.totalPages) {
      return;
    }
    this.pageIndex = index;
    this.updatePagedItems();
  }

  nextPage(): void {
    this.goToPage(this.pageIndex + 1);
  }

  prevPage(): void {
    this.goToPage(this.pageIndex - 1);
  }

  delete(item: EmployeeModel) {
    swal({
      title: "Are you sure?",
      text: "You won't be able to revert this!",
      icon: "warning",

      dangerMode: true,
      buttons: ["Cancel", "Yes,Delete it!"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          this.employeeService.delete(this.companyId,item).subscribe(result => {
            swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
            this.ngOnInit()
          })
        }

      });
  }

  new() {
    this.isEdit = false
    this.selectModel = new EmployeeModel()
  }

  downloadImportTemplate(): void {
    this.employeeService.downloadImportTemplate(this.companyId).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'employee-import-template.xlsx';
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err) => {
        void this.resolveBlobError(err).then((msg) =>
          swal('ดาวน์โหลดไม่สำเร็จ', msg, 'error'),
        );
      },
    });
  }

  private async resolveBlobError(err: any): Promise<string> {
    if (err?.error instanceof Blob) {
      try {
        const text = await err.error.text();
        const json = JSON.parse(text);
        if (typeof json?.detail === 'string') {
          return this.translateApiMessage(json.detail);
        }
      } catch {
        /* fall through */
      }
    }
    return this.formatApiError(err);
  }

  triggerImportFile(): void {
    if (this.isImporting) {
      return;
    }
    this.pendingImportExcel = null;
    if (this.importFileInput?.nativeElement) {
      this.importFileInput.nativeElement.value = '';
      this.importFileInput.nativeElement.click();
    }
  }

  onImportFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    const name = (file.name || '').toLowerCase();
    if (!name.endsWith('.xlsx') && !name.endsWith('.xlsm')) {
      swal('ไฟล์ไม่ถูกต้อง', 'กรุณาเลือกไฟล์ Excel (.xlsx)', 'warning');
      input.value = '';
      return;
    }

    this.pendingImportExcel = file;
    input.value = '';

    swal({
      title: 'นำเข้าพนักงานจาก Excel?',
      text:
        `ไฟล์: ${file.name}\n\n` +
        'ต้องการแนบ ZIP รูปใบหน้าด้วยหรือไม่?\n' +
        '(ชื่อไฟล์ใน ZIP ควรตรงคอลัมน์ ไฟล์รูปใบหน้า หรือใช้อีเมล/รหัสพนักงาน)',
      icon: 'info',
      buttons: {
        cancel: { text: 'Cancel', value: null, visible: true },
        skip: { text: 'นำเข้าโดยไม่มีรูป', value: 'skip' },
        zip: { text: 'แนบ ZIP รูป', value: 'zip' },
      } as any,
    }).then((choice: any) => {
      if (!choice) {
        this.pendingImportExcel = null;
        return;
      }
      if (choice === 'zip') {
        if (this.importPhotosInput?.nativeElement) {
          this.importPhotosInput.nativeElement.value = '';
          this.importPhotosInput.nativeElement.click();
        }
        return;
      }
      this.runEmployeeImport(null);
    });
  }

  onImportPhotosSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const zip = input.files?.[0] || null;
    input.value = '';
    if (!this.pendingImportExcel) {
      return;
    }
    if (zip) {
      const name = (zip.name || '').toLowerCase();
      if (!name.endsWith('.zip')) {
        swal('ไฟล์ไม่ถูกต้อง', 'กรุณาเลือกไฟล์ ZIP ของรูปใบหน้า', 'warning');
        this.pendingImportExcel = null;
        return;
      }
    }
    this.runEmployeeImport(zip);
  }

  private runEmployeeImport(photosZip: File | null): void {
    const file = this.pendingImportExcel;
    this.pendingImportExcel = null;
    if (!file) {
      return;
    }
    this.isImporting = true;
    this.cdr.detectChanges();
    this.employeeService.startImportJob(this.companyId, file, photosZip).subscribe({
      next: (job) => this.pollImportJob(job.jobId),
      error: (err) => {
        this.isImporting = false;
        this.cdr.detectChanges();
        swal('นำเข้าไม่สำเร็จ', this.formatApiError(err), 'error');
      },
    });
  }

  private pollImportJob(jobId: string): void {
    this.employeeService.importJob(this.companyId, jobId).subscribe({
      next: (job) => {
        if (job.status === 'done') {
          this.isImporting = false;
          this.cdr.detectChanges();
          this.ngOnInit();
          this.showImportResult(job.result || { total: 0, success: 0, failed: 0 });
          return;
        }
        if (job.status === 'failed') {
          this.isImporting = false;
          this.cdr.detectChanges();
          swal('นำเข้าไม่สำเร็จ', job.error || 'import failed', 'error');
          return;
        }
        setTimeout(() => this.pollImportJob(jobId), 2000);
      },
      error: (err) => {
        this.isImporting = false;
        this.cdr.detectChanges();
        swal('นำเข้าไม่สำเร็จ', this.formatApiError(err), 'error');
      },
    });
  }

  private showImportResult(result: {
    total: number;
    success: number;
    failed: number;
    facesEnrolled?: number;
    created?: { faceEnrolled?: boolean; faceWarning?: string | null; row: number; email: string }[];
    errors?: { row: number; email: string; message: string }[];
  }): void {
    const faceWarnLines = (result.created || [])
      .filter((c) => c.faceWarning)
      .slice(0, 5)
      .map(
        (c) =>
          `• แถว ${c.row}${c.email ? ` (${c.email})` : ''}: บันทึกพนักงานแล้ว แต่ใบหน้าไม่สำเร็จ — ${c.faceWarning}`,
      );
    const errorLines = (result.errors || [])
      .slice(0, 8)
      .map((e) => `• แถว ${e.row}${e.email ? ` (${e.email})` : ''}: ${e.message}`);
    const more =
      (result.errors?.length || 0) > 8
        ? `\n…และอีก ${(result.errors!.length - 8)} รายการ`
        : '';
    const faces = result.facesEnrolled ?? 0;
    const text = [
      `ทั้งหมด ${result.total} แถว`,
      `สำเร็จ ${result.success} รายการ`,
      `ลงทะเบียนใบหน้า ${faces} รายการ`,
      `ไม่สำเร็จ ${result.failed} รายการ`,
      faceWarnLines.length
        ? '\nคำเตือนรูปใบหน้า:\n' + faceWarnLines.join('\n')
        : '',
      errorLines.length ? '\nรายละเอียดข้อผิดพลาด:\n' + errorLines.join('\n') + more : '',
    ]
      .filter(Boolean)
      .join('\n');

    const hasFaceWarn = faceWarnLines.length > 0;
    const icon =
      result.failed === 0 && !hasFaceWarn
        ? 'success'
        : result.success > 0
          ? 'warning'
          : 'error';
    const title =
      result.failed === 0 && !hasFaceWarn
        ? 'นำเข้าสำเร็จ'
        : result.success > 0
          ? 'นำเข้าบางส่วนสำเร็จ'
          : 'นำเข้าไม่สำเร็จ';
    swal({ title, text, icon });
  }

  view(item: EmployeeModel) {
    console.log(item)
    this.isEdit = true;
    this.selectModel = item
  }

  openFaceManagementModal(item: any): void {
    if (item && item.member && item.member.memberId) {
      this.selectedMemberId = item.member.memberId;
      const first = item.member.firstName || item.firstName || '';
      const last = item.member.lastName || item.lastName || '';
      this.selectedMemberName =
        [first, last].filter(Boolean).join(' ').trim() ||
        item.employeeCode ||
        item.member.memberId;
    } else {
      console.error('Could not get memberId from the selected item.');
    }
  }

  save() {
    const clientError = this.validateEmployeeForm();
    if (clientError) {
      swal('ไม่สามารถบันทึกได้', clientError, 'warning');
      return;
    }

    swal({
      title: "Are you sure?",
      text: "คุณต้องการบันทึกหรือไม่",
      icon: "warning",
      dangerMode: false,
      buttons: ["Cancel", "Confirm"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          if (!this.isEdit) {
            if (this.selectModel.companyRoleType === undefined || this.selectModel.companyRoleType === null) {
              this.selectModel.companyRoleType = 0;
            }
            this.employeeService.save(this.selectModel, this.companyId).subscribe({
              next: () => {
                swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
                this.ngOnInit();
                this.childModal?.nativeElement.click();
              },
              error: (err) => this.showSaveError(err),
            });
          } else {
            this.employeeService.update(this.selectModel, this.companyId).subscribe({
              next: () => {
                swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
                this.ngOnInit();
                this.childModal?.nativeElement.click();
              },
              error: (err) => this.showSaveError(err),
            });
          }
        }
      });
  }

  private validateEmployeeForm(): string | null {
    const email = (this.selectModel?.member?.email || '').trim();
    if (!email) {
      return 'กรุณากรอกอีเมล';
    }
    // Match EmailStr: local@domain with a dot in the domain (e.g. name@company.com)
    const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    if (!emailOk) {
      return `รูปแบบอีเมลไม่ถูกต้อง: "${email}"\nตัวอย่างที่ถูกต้อง: name@company.com\n(ต้องมีเครื่องหมาย @ และจุดในโดเมน)`;
    }
    if (!this.selectModel?.member?.firstName?.trim()) {
      return 'กรุณากรอกชื่อ';
    }
    if (!this.selectModel?.member?.lastName?.trim()) {
      return 'กรุณากรอกนามสกุล';
    }
    if (!this.selectModel?.department?.departmentId) {
      return 'กรุณาเลือกแผนก';
    }
    if (!this.selectModel?.position?.positionId) {
      return 'กรุณาเลือกตำแหน่ง';
    }
    if (this.selectModel.empType === undefined || this.selectModel.empType === null) {
      return 'กรุณาเลือกประเภทพนักงาน (รายวัน/รายเดือน)';
    }
    return null;
  }

  private showSaveError(err: any): void {
    const detail = this.formatApiError(err);
    const status = err?.status;
    const title =
      status === 422
        ? 'ข้อมูลไม่ถูกต้อง (422)'
        : status === 400
          ? 'ไม่สามารถเพิ่มพนักงานได้'
          : status === 409
            ? 'ข้อมูลซ้ำ'
            : 'บันทึกไม่สำเร็จ';
    swal({
      title,
      text: detail,
      icon: 'error',
    });
  }

  private formatApiError(err: any): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string') {
      return this.translateApiMessage(detail);
    }
    if (Array.isArray(detail)) {
      const lines = detail.map((d: any) => this.translateValidationItem(d));
      return lines.filter(Boolean).join('\n') || 'กรุณาตรวจสอบข้อมูลแล้วลองใหม่';
    }
    if (err?.status === 0) {
      return 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองใหม่';
    }
    return err?.message || 'กรุณาตรวจสอบข้อมูลแล้วลองใหม่';
  }

  private translateValidationItem(d: any): string {
    const locParts = Array.isArray(d?.loc)
      ? d.loc.filter((x: any) => x !== 'body' && typeof x === 'string')
      : [];
    const fieldKey = locParts[locParts.length - 1] || '';
    const fieldLabel = this.fieldLabelTh(fieldKey, locParts);
    const msg = this.translateApiMessage(String(d?.msg || ''));
    if (fieldLabel && msg) {
      return `• ${fieldLabel}: ${msg}`;
    }
    return msg ? `• ${msg}` : '';
  }

  private fieldLabelTh(field: string, locParts: string[] = []): string {
    const map: Record<string, string> = {
      email: 'อีเมล',
      firstName: 'ชื่อ',
      lastName: 'นามสกุล',
      phoneNumber: 'เบอร์โทร',
      birthDate: 'วันเกิด',
      address: 'ที่อยู่',
      emergencyContactName: 'ผู้ติดต่อฉุกเฉิน',
      emergencyContactPhone: 'เบอร์ติดต่อฉุกเฉิน',
      employeeId: 'รหัสพนักงาน',
      salary: 'เงินเดือน',
      bossId: 'หัวหน้างาน',
      startDate: 'วันเริ่มงาน',
      empType: 'ประเภทพนักงาน',
      companyRoleType: 'สิทธิ์การใช้งาน',
      position: 'ตำแหน่ง',
      department: 'แผนก',
      positionId: 'ตำแหน่ง',
      departmentId: 'แผนก',
      member: 'ข้อมูลสมาชิก',
    };
    if (map[field]) {
      return map[field];
    }
    if (locParts.includes('email')) {
      return 'อีเมล';
    }
    return field || 'ข้อมูล';
  }

  private translateApiMessage(msg: string): string {
    const m = (msg || '').toLowerCase();
    if (m.includes('not a valid email') || m.includes('value is not a valid email')) {
      if (m.includes('period') || m.includes('dot')) {
        return 'รูปแบบอีเมลไม่ถูกต้อง — หลัง @ ต้องมีจุด เช่น name@company.com (ตอนนี้ใช้แบบ name@sss ไม่ได้)';
      }
      return 'รูปแบบอีเมลไม่ถูกต้อง กรุณาใช้รูปแบบ name@company.com';
    }
    if (m.includes('already registered') || m.includes('already exists')) {
      return 'อีเมลนี้มีพนักงานในบริษัทนี้อยู่แล้ว';
    }
    if (m.includes('field required') || m.includes('missing')) {
      return 'ยังไม่ได้กรอก / เลือกค่านี้';
    }
    if (m.includes('valid date') || m.includes('datetime')) {
      return 'รูปแบบวันที่ไม่ถูกต้อง';
    }
    if (m.includes('กรุณาเลือก')) {
      return msg;
    }
    return msg || 'ข้อมูลไม่ถูกต้อง';
  }

  updateEmp() {
    this.save();
  }

  // filterEmp(empId: string) {
  //   this.selectModel.supervisor = this.itemsList.filter(e => e.employeeId == empId)[0]
  // }

  updatePagedItems(): void {
    if (!this.filteredSource?.length && !this._searchTerm) {
      this.filteredSource = [...(this.itemsList || [])];
    }
    const startIndex = this.pageIndex * this.pageSize;
    this.filterList = this.filteredSource.slice(startIndex, startIndex + this.pageSize);
  }
}

