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
import * as faceapi from 'face-api.js';
import { FaceManagementComponent } from '../dialogs/face-management/face-management.component';
import { firstValueFrom } from 'rxjs';
import { playCaptureBeep, unlockBeepAudio } from '../../../shared/utils/beep';

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
  filterList: EmployeeModel[] = []
  selectModel: EmployeeModel = new EmployeeModel()
  selectedItems = new Map<string, boolean>();
  departmentList: DepartmentModel[] = []
  positionList: PositionModel[] = []
  pageIndex = 0;
  public selectedMemberId: string | null = null;
  get searchTerm(): string {
    return this._searchTerm;
  }
  set searchTerm(val: string) {
    this.pageIndex = 0;
    this.allSelected = false
    this._searchTerm = val;
    if (val != '') {
      this.filterList = this.filter(val);
    } else {
      this.updatePagedItems()
    }
  }
  companyId = ""
  _searchTerm = "";
  isEdit = false;
  constructor(
    private http: HttpClient,
    private employeeService: EmployeeService,
    public translate: TranslateService,
    private departmentService: DepartmentService,
    private positionService: PositionService,
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
  private modelsLoaded = false;
  private faceDetectionInterval: ReturnType<typeof setInterval> | null = null;
  private videoStream: MediaStream | null = null;
  private smoothedBox: SmoothBox | null = null;
  private poseHoldStartedAt = 0;
  private capturingAngle = false;
  private readonly boxLerp = 0.35;
  private readonly poseHoldMs = 700;
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
    this.stopFaceCamera();
    this.movedModalNodes.forEach((el) => el.remove());
    this.movedModalNodes = [];
  }

  async openFaceEnroll(item: EmployeeModel): Promise<void> {
    this.view(item);
    this.resetFaceAngles();
    this.checkMatch = false;
    this.isFaceDetected = false;
    this.capturingAngle = false;
    this.smoothedBox = null;
    this.poseHoldStartedAt = 0;
    this.uploadProgressLabel = '';
    this.faceStatus = 'กำลังโหลดโมเดลและกล้อง...';
    this.cdr.detectChanges();

    try {
      unlockBeepAudio();
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
    await Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri('/assets/models/tiny_face_detector'),
      faceapi.nets.faceLandmark68Net.loadFromUri('/assets/models/face_landmark_68'),
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
          const label = step
            ? (poseOk ? `${step.label} ✓` : step.label)
            : 'ครบ 5 มุม';

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
                this.faceStatus = poseOk
                  ? `มุม ${this.currentAngleIndex + 1}/5 — พร้อมถ่าย`
                  : `มุม ${this.currentAngleIndex + 1}/5 — ${step.hint}`;
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
      swal('Save Success!!', 'บันทึกใบหน้า 5 มุมสำเร็จ', 'success');
      this.childModalFace?.nativeElement.click();
      this.stopFaceCamera();
    } catch (error: any) {
      const detail = error?.error?.detail || 'บันทึกใบหน้าไม่สำเร็จ';
      this.uploadStatus = 'Error uploading face!';
      this.faceStatus = detail;
      this.cdr.detectChanges();
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
    // Non-mirrored camera: user turns left → nose shifts toward image-right → yaw > 0
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
        // User turns their left → nose moves toward image-right
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
    this.getDepartment()
    this.getPosition()

    this.employeeService.getLists(this.companyId).subscribe(result => {
      this.itemsList = result
      this.updatePagedItems()
    })
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

  filter(v: string) {
    this.pageIndex = 0;
    return this.itemsList?.filter(
      (x) =>
        x.company_employeeId?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.employeeId?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.getFullname()?.toLowerCase().indexOf(v.toLowerCase()) !== -1
        ||
        x.getType()?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.getRole()?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.position.getName().toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.department.getName().toLowerCase().indexOf(v.toLowerCase()) !== -1
    );
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

  view(item: EmployeeModel) {
    console.log(item)
    this.isEdit = true;
    this.selectModel = item
  }

  openFaceManagementModal(item: any): void {
    if (item && item.member && item.member.memberId) {
      this.selectedMemberId = item.member.memberId;
    } else {
      console.error("Could not get memberId from the selected item.");
    }
  }

  save() {
    if (!this.selectModel?.member?.email) {
      swal('ข้อมูลไม่ครบ', 'กรุณากรอกอีเมล', 'info');
      return;
    }
    if (!this.selectModel?.department?.departmentId) {
      swal('ข้อมูลไม่ครบ', 'กรุณาเลือกแผนก', 'info');
      return;
    }
    if (!this.selectModel?.position?.positionId) {
      swal('ข้อมูลไม่ครบ', 'กรุณาเลือกตำแหน่ง', 'info');
      return;
    }
    if (this.selectModel.empType === undefined || this.selectModel.empType === null) {
      swal('ข้อมูลไม่ครบ', 'กรุณาเลือกประเภทพนักงาน', 'info');
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
              error: (err) => {
                const detail = this.formatApiError(err);
                swal('บันทึกไม่สำเร็จ', detail, 'error');
              },
            });
          } else {
            this.employeeService.update(this.selectModel, this.companyId).subscribe({
              next: () => {
                swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
                this.ngOnInit();
                this.childModal?.nativeElement.click();
              },
              error: (err) => {
                const detail = this.formatApiError(err);
                swal('บันทึกไม่สำเร็จ', detail, 'error');
              },
            });
          }
        }
      });
  }

  private formatApiError(err: any): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((d: any) => {
          const loc = Array.isArray(d.loc) ? d.loc.filter((x: any) => x !== 'body').join('.') : '';
          return loc ? `${loc}: ${d.msg}` : d.msg;
        })
        .join('\n');
    }
    return err?.message || 'กรุณาตรวจสอบข้อมูลแล้วลองใหม่';
  }

  updateEmp() {
    swal({
      title: "Are you sure?",
      text: "คุณต้องการบันทึกหรือไม่",
      icon: "warning",
      dangerMode: false,
      buttons: ["Cancel", "Confirm"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          this.employeeService.save(this.selectModel, this.companyId).subscribe(result => {
            swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
            this.ngOnInit()
            this.childModal?.nativeElement.click()
          })
        }

      });


  }

  // filterEmp(empId: string) {
  //   this.selectModel.supervisor = this.itemsList.filter(e => e.employeeId == empId)[0]
  // }

  updatePagedItems() {
    const startIndex = this.pageIndex * 10;
    const endIndex = startIndex + 10;
    // this.filterList = this.itemsList.slice(startIndex, endIndex);
    this.filterList = this.itemsList
  }
}
