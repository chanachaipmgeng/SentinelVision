import {
  Component,
  ElementRef,
  Input,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { environment } from '../../../../../environments/environment';
import { firstValueFrom } from 'rxjs';
import swal from 'sweetalert';

interface FaceEncoding {
  faceEncodingId: string;
  memberId: string;
  createdAt: string;
  imageUrl: string;
}

interface VerifyResult {
  matched: boolean;
  confidencePercent: number;
  confidence: number;
  distance: number;
  threshold: number;
  matchQuality: string;
  faceEncodingId?: string;
  member?: {
    fullName?: string;
    firstName?: string;
    lastName?: string;
  };
  message?: string;
}

@Component({
  selector: 'app-face-management',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './face-management.component.html',
  styleUrls: ['./face-management.component.css'],
})
export class FaceManagementComponent implements OnInit, OnDestroy {
  @Input() memberId!: string;

  @ViewChild('verifyVideo') verifyVideo?: ElementRef<HTMLVideoElement>;
  @ViewChild('verifyFileInput') verifyFileInput?: ElementRef<HTMLInputElement>;

  encodings: FaceEncoding[] = [];
  isLoading = true;
  error: string | null = null;

  cameraOn = false;
  isVerifying = false;
  verifyPreview: string | null = null;
  verifyResult: VerifyResult | null = null;
  verifyError: string | null = null;

  private videoStream: MediaStream | null = null;
  private pendingFile: File | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    if (this.memberId) {
      this.loadEncodings();
    } else {
      this.error = 'ไม่พบรหัสพนักงาน';
      this.isLoading = false;
    }
  }

  ngOnDestroy(): void {
    this.stopCamera();
    this.clearVerifyPreview();
  }

  loadEncodings(): void {
    this.isLoading = true;
    this.error = null;
    this.http
      .get<FaceEncoding[]>(
        `${environment.baseUrl}/face/members/${this.memberId}/encodings`,
      )
      .subscribe({
        next: (data) => {
          this.encodings = data;
          this.isLoading = false;
        },
        error: (err) => {
          this.error = 'โหลดรายการใบหน้าไม่สำเร็จ';
          console.error(err);
          this.isLoading = false;
        },
      });
  }

  deleteEncoding(encodingId: string): void {
    swal({
      title: 'ลบใบหน้านี้?',
      text: 'เมื่อลบแล้วจะกู้คืนไม่ได้',
      icon: 'warning',
      buttons: ['ยกเลิก', 'ลบ'],
      dangerMode: true,
    }).then((willDelete) => {
      if (!willDelete) {
        return;
      }
      this.http
        .delete(`${environment.baseUrl}/face/encodings/${encodingId}`)
        .subscribe({
          next: () => {
            swal('ลบสำเร็จ', 'ลบใบหน้าแล้ว', 'success');
            this.loadEncodings();
          },
          error: (err) => {
            swal('ลบไม่สำเร็จ', this.formatError(err), 'error');
            console.error(err);
          },
        });
    });
  }

  clearAllEncodings(): void {
    if (!this.encodings.length) {
      swal('ไม่มีข้อมูล', 'ยังไม่มีใบหน้าที่ลงทะเบียน', 'info');
      return;
    }
    swal({
      title: 'ล้างการลงทะเบียนใบหน้าทั้งหมด?',
      text: `จะลบ ${this.encodings.length} รายการของพนักงานคนนี้ และกู้คืนไม่ได้`,
      icon: 'warning',
      buttons: ['ยกเลิก', 'ล้างทั้งหมด'],
      dangerMode: true,
    }).then((ok) => {
      if (!ok) {
        return;
      }
      this.http
        .delete(`${environment.baseUrl}/face/members/${this.memberId}/encodings`)
        .subscribe({
          next: (res: any) => {
            swal(
              'ล้างสำเร็จ',
              `ลบใบหน้าแล้ว ${res?.deleted ?? this.encodings.length} รายการ`,
              'success',
            );
            this.verifyResult = null;
            this.verifyError = null;
            this.clearVerifyPreview();
            this.loadEncodings();
          },
          error: (err) => {
            swal('ล้างไม่สำเร็จ', this.formatError(err), 'error');
            console.error(err);
          },
        });
    });
  }

  async startCamera(): Promise<void> {
    this.verifyResult = null;
    this.verifyError = null;
    this.clearVerifyPreview();
    try {
      this.stopCamera();
      this.videoStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
      this.cameraOn = true;
      setTimeout(() => {
        if (this.verifyVideo?.nativeElement) {
          this.verifyVideo.nativeElement.srcObject = this.videoStream;
        }
      }, 0);
    } catch (err) {
      console.error(err);
      this.cameraOn = false;
      swal('เปิดกล้องไม่สำเร็จ', 'กรุณาอนุญาตการใช้กล้องในเบราว์เซอร์', 'error');
    }
  }

  stopCamera(): void {
    if (this.videoStream) {
      this.videoStream.getTracks().forEach((t) => t.stop());
      this.videoStream = null;
    }
    if (this.verifyVideo?.nativeElement) {
      this.verifyVideo.nativeElement.srcObject = null;
    }
    this.cameraOn = false;
  }

  captureFromCamera(): void {
    const video = this.verifyVideo?.nativeElement;
    if (!video || !this.cameraOn) {
      swal('ยังไม่พร้อม', 'กรุณาเปิดกล้องก่อน', 'info');
      return;
    }
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    this.clearVerifyPreview();
    this.verifyPreview = canvas.toDataURL('image/jpeg', 0.92);
    this.verifyResult = null;
    this.verifyError = null;
  }

  triggerVerifyFile(): void {
    if (this.verifyFileInput?.nativeElement) {
      this.verifyFileInput.nativeElement.value = '';
      this.verifyFileInput.nativeElement.click();
    }
  }

  onVerifyFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) {
      return;
    }
    this.stopCamera();
    this.clearVerifyPreview();
    this.verifyPreview = URL.createObjectURL(file);
    this.verifyResult = null;
    this.verifyError = null;
    this.pendingFile = file;
  }

  private clearVerifyPreview(): void {
    if (this.verifyPreview?.startsWith('blob:')) {
      URL.revokeObjectURL(this.verifyPreview);
    }
    this.verifyPreview = null;
    this.pendingFile = null;
  }

  async runVerify(): Promise<void> {
    if (!this.memberId) {
      return;
    }
    if (!this.encodings.length) {
      swal('ยังไม่มีใบหน้า', 'กรุณาลงทะเบียนใบหน้าก่อนทดสอบ', 'info');
      return;
    }

    if (this.cameraOn && !this.verifyPreview) {
      this.captureFromCamera();
    }

    let file: File | null = this.pendingFile;
    if (!file && this.verifyPreview?.startsWith('data:')) {
      file = this.dataURLtoFile(this.verifyPreview, 'verify-face.jpg');
    }
    if (!file) {
      swal('ยังไม่มีรูป', 'ถ่ายจากกล้องหรืออัปโหลดรูปก่อนทดสอบ', 'info');
      return;
    }

    this.isVerifying = true;
    this.verifyResult = null;
    this.verifyError = null;
    try {
      const formData = new FormData();
      formData.append('file', file, file.name || 'verify-face.jpg');
      const result = await firstValueFrom(
        this.http.post<VerifyResult>(
          `${environment.baseUrl}/face/members/${this.memberId}/verify`,
          formData,
        ),
      );
      this.verifyResult = result;
    } catch (err: any) {
      this.verifyError = this.formatError(err);
      this.verifyResult = null;
    } finally {
      this.isVerifying = false;
    }
  }

  getFullImageUrl(relativeUrl: string): string {
    return `${environment.baseUrl}${relativeUrl}`;
  }

  qualityLabel(q: string | undefined): string {
    if (q === 'high') return 'สูง';
    if (q === 'medium') return 'ปานกลาง';
    if (q === 'low') return 'ต่ำ';
    return q || '-';
  }

  private formatError(err: any): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    return 'เกิดข้อผิดพลาด กรุณาลองใหม่';
  }

  private dataURLtoFile(dataurl: string, filename: string): File {
    const arr = dataurl.split(',');
    const mime = arr[0].match(/:(.*?);/)?.[1] || 'image/jpeg';
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: mime });
  }
}
