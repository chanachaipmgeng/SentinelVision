import { Component, ViewChild, ElementRef, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import * as faceapi from 'face-api.js';
import { environment } from 'src/environments/environment';
import { TimestampService } from 'src/app/shared/services/timestamp.service';
import { TimestampModel } from 'src/app/shared/models/timestamp.model';
import { TokenService } from 'src/app/shared/services/token.service';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import swal from 'sweetalert';
import { CompanyLocationModel } from 'src/app/shared/models/company-location.model';
import { CompanyLocationService } from 'src/app/shared/services/company-location.service';
import { assetUrl } from 'src/app/shared/utils/asset-url';
import { playCheckInBeep, unlockBeepAudio } from 'src/app/shared/utils/beep';

@Component({
  selector: 'app-face-scan',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
  ],
  templateUrl: './face-scan.component.html',
  styleUrls: ['./face-scan.component.css'],
})
export class FaceScanComponent implements OnDestroy {
  @ViewChild('video') video: ElementRef;
  @ViewChild('canvas') canvas: ElementRef;

  locationList: CompanyLocationModel[] = [];
  locationArea: CompanyLocationModel[] = [];
  
  companyId = "";
  memberId = ""; // We get this from the backend now
  timestampModel: TimestampModel = new TimestampModel();
  employeeModel: EmployeeModel = new EmployeeModel();
  location: { latitude: number; longitude: number } = { latitude: 0, longitude: 0 };
  errorMessage: string | null = null;
  outOfAreaNote = '';

  // --- New state variables ---
  isCapturing = false;
  captureProgress = 0;
  captureMessage = 'Please look at the camera.';
  faceDetectionInterval: any;
  videoStream: MediaStream | null = null;

  constructor(
    private http: HttpClient, 
    private timestampService: TimestampService, 
    private tokenService: TokenService, 
    private employeeService: EmployeeService, 
    private comLocationService: CompanyLocationService
  ) {
    this.companyId = this.tokenService.getSelectCompany().companyId;
    // We don't need to get memberId beforehand anymore for the 1:N check
  }

  ngOnInit() {
    unlockBeepAudio();
    this.loadModelsAndStartVideo();
    this.getCompanyLocation();
  }

  ngOnDestroy() {
    // Clean up resources
    clearInterval(this.faceDetectionInterval);
    if (this.videoStream) {
      this.videoStream.getTracks().forEach(track => track.stop());
    }
  }

  async loadModelsAndStartVideo() {
    const modelsBase = assetUrl('assets/models');
    await Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri(`${modelsBase}/tiny_face_detector`),
      faceapi.nets.faceLandmark68Net.loadFromUri(`${modelsBase}/face_landmark_68`),
      faceapi.nets.faceRecognitionNet.loadFromUri(`${modelsBase}/face_recognition`),
    ]);
    this.startVideo();
  }

  startVideo(): void {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        this.videoStream = stream;
        this.video.nativeElement.srcObject = stream;
        this.startFaceDetection();
      })
      .catch(err => {
        console.error('Error accessing camera: ', err);
        this.captureMessage = 'Could not access the camera.';
      });
  }

  startFaceDetection(): void {
    const videoEl = this.video.nativeElement;
    const displaySize = { width: videoEl.width, height: videoEl.height };
    faceapi.matchDimensions(this.canvas.nativeElement, displaySize);

    this.faceDetectionInterval = setInterval(async () => {
      if (this.isCapturing) return; // Don't detect while capturing

      const detections = await faceapi.detectSingleFace(videoEl, new faceapi.TinyFaceDetectorOptions());
      const context = this.canvas.nativeElement.getContext('2d');
      context.clearRect(0, 0, displaySize.width, displaySize.height);

      if (detections) {
        const resizedDetections = faceapi.resizeResults(detections, displaySize);
        faceapi.draw.drawDetections(this.canvas.nativeElement, resizedDetections!);
        this.captureMessage = 'Face detected. Ready to check in.';
      } else {
        this.captureMessage = 'Please position your face in the center.';
      }
    }, 500); // Detect every 500ms
  }

  // --- Main function to be called by a button click ---
  async onCheckInClick() {
    if (this.isCapturing) return;

    this.isCapturing = true;
    this.captureMessage = 'Starting liveness check... Please hold still.';
    this.captureProgress = 0;

    const capturedFrames: string[] = [];
    const frameCount = 10; // Capture 10 frames
    const captureInterval = 150; // every 150ms

    const captureProcess = setInterval(() => {
      if (capturedFrames.length >= frameCount) {
        clearInterval(captureProcess);
        this.sendFramesForVerification(capturedFrames);
        return;
      }

      const frame = this.captureFrame();
      capturedFrames.push(frame);
      this.captureProgress = (capturedFrames.length / frameCount) * 100;
    }, captureInterval);
  }

  captureFrame(): string {
    const video = this.video.nativeElement;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    context?.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg');
  }

  async sendFramesForVerification(frames: string[]) {
    if (!this.hasValidLocation()) {
      swal(
        'ยังไม่มีพิกัด GPS',
        this.errorMessage || 'กรุณาอนุญาตตำแหน่งก่อนลงเวลา (ต้องใช้ HTTPS)',
        'warning',
      );
      this.resetCaptureState();
      this.getCurrentLocation();
      return;
    }

    this.captureMessage = 'Verifying...';
    const formData = new FormData();
    frames.forEach((dataUrl, index) => {
      const file = this.dataURLtoFile(dataUrl, `frame_${index}.jpg`);
      formData.append('files', file);
    });

    // *** IMPORTANT: Using the new endpoint for 1:N check with liveness ***
    this.http.post(environment.baseUrl + `/face/members/check-face-emp`, formData).subscribe({
      next: (response: any) => {
        this.memberId = response.memberId; // Get the memberId from the successful response
        this.captureMessage = 'Liveness check passed! Saving timestamp.';
        this.uploadPhotoAndSaveTimestamp(frames[Math.floor(frames.length / 2)]); // Use middle frame for thumbnail
      },
      error: (error) => {
        const detail = error.error?.detail || 'Liveness check failed. Please try again.';
        swal("Verification Failed", detail, "error");
        this.resetCaptureState();
      }
    });
  }

  uploadPhotoAndSaveTimestamp(thumbnailFrame: string) {
    const file = this.dataURLtoFile(thumbnailFrame, 'timestamp_photo.jpg');
    const formData = new FormData();
    formData.append('file', file);

    this.http.post(environment.baseUrl + `/api/upload-image/`, formData).subscribe({
      next: (response: any) => {
        this.timestampModel.photoTimestamp = response.filename;
        this.saveTimestamp();
      },
      error: (error) => {
        swal("Photo Upload Failed", error.error?.detail || 'Could not save photo.', "error");
        this.resetCaptureState();
      }
    });
  }

  private hasValidLocation(): boolean {
    const lat = Number(this.location?.latitude);
    const lng = Number(this.location?.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      return false;
    }
    return Math.abs(lat) > 0.0001 || Math.abs(lng) > 0.0001;
  }

  saveTimestamp() {
    if (!this.hasValidLocation()) {
      swal(
        'ยังไม่มีพิกัด GPS',
        this.errorMessage || 'กรุณาอนุญาตตำแหน่งในเบราว์เซอร์ แล้วลองลงเวลาใหม่ (ต้องใช้ HTTPS)',
        'warning',
      );
      this.resetCaptureState();
      this.getCurrentLocation();
      return;
    }

    // First, get the latest employee info using the verified memberId
    this.employeeService.getMemberById(this.companyId, this.memberId).subscribe(employeeResult => {
      this.employeeModel = employeeResult;
      this.timestampModel.company_employeeId = this.employeeModel.company_employeeId;

      const outside = this.locationArea.length === 0;
      if (outside) {
        const note = (this.outOfAreaNote || '').trim();
        if (!note) {
          swal("ต้องระบุเหตุผล", "อยู่นอกพื้นที่ลงเวลา กรุณากรอกหมายเหตุก่อน Check-In", "info");
          this.resetCaptureState();
          return;
        }
        this.timestampModel.timestampType = 0;
        this.timestampModel.note = note;
      } else {
        this.timestampModel.timestampType = 1;
        this.timestampModel.locationName = this.locationArea[0].locationName;
        this.timestampModel.note = '';
      }
      this.timestampModel.latitude = this.location.latitude;
      this.timestampModel.longitude = this.location.longitude;

      this.timestampService.save(this.companyId, this.timestampModel).subscribe({
        next: (result) => {
          const pending = result.approvalStatus === 'PENDING' || result.timestampType == 0;
          playCheckInBeep();
          swal(
            pending ? "รออนุมัติ !!" : "Complete !!",
            `ลงเวลาการทำงาน ${this.employeeModel.getFullname()} เวลา ${new Date(result.timestamp).toLocaleTimeString("th", { hour: '2-digit', minute: '2-digit' })}`,
            pending ? "info" : "success"
          ).then(() => {
            this.outOfAreaNote = '';
            this.resetCaptureState();
          });
        },
        error: (err) => {
          swal("บันทึกไม่สำเร็จ", err.error?.detail || 'กรุณาลองใหม่', "error");
          this.resetCaptureState();
        }
      });
    });
  }

  resetCaptureState() {
    this.isCapturing = false;
    this.captureProgress = 0;
    this.captureMessage = 'Please position your face in the center.';
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

  // --- Location methods remain the same ---
  getCompanyLocation() {
    this.comLocationService.getLists(this.companyId).subscribe(result => {
      this.locationList = result;
      this.getCurrentLocation();
    });
  }

  getCurrentLocation() {
    if (!navigator.geolocation) {
      this.errorMessage = 'เบราว์เซอร์นี้ไม่รองรับ Geolocation';
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        this.location = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        };
        this.searchCompanyLocation();
        this.errorMessage = null;
      },
      () => {
        this.errorMessage = 'อ่านตำแหน่งไม่ได้ กรุณาเปิด GPS และอนุญาต Location (ต้องใช้ HTTPS)';
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 },
    );
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
    const distance = R * c;
    return distance;
  }

  searchCompanyLocation() {
    this.locationArea = this.getFilteredLocations();
  }

  getFilteredLocations(): CompanyLocationModel[] {
    return this.locationList.filter(location => {
      const distance = this.getDistance(
        this.location.latitude.toString(),
        this.location.longitude.toString(),
        location.latitude.toString(),
        location.longitude.toString()
      );
      return distance <= location.radius;
    });
  }
}
