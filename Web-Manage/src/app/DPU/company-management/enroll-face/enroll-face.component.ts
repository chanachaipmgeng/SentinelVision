import { HttpClient } from '@angular/common/http';
import { Component, ElementRef, OnDestroy, ViewChild } from '@angular/core';
import * as faceapi from 'face-api.js';

import swal from 'sweetalert';
import { environment } from '../../../../environments/environment';
import { CommonModule } from '@angular/common';
import { TokenService } from '../../../shared/services/token.service';
import { SharedModule } from '../../../shared/shared.module';
import { TimestampModel } from '../../models/timestamp.model';
import { EmployeeModel } from '../../models/employee.model';
import { TimestampService } from '../../services/timestamp.service';
import { EmployeeService } from '../../services/employee.service';
import { CompanyLocationModel } from '../../models/company-location.model';
import { CompanyLocationService } from '../../services/company-location.service';

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
  capturedImage: string | null = null;
  checkMatch = false;
  companyId = '';
  memberId = '';
  timestampModel: TimestampModel = new TimestampModel();
  employeeModel: EmployeeModel = new EmployeeModel();
  location: { latitude: number; longitude: number } = { latitude: 0, longitude: 0 };
  errorMessage: string | null = null;

  isCapturing = false;
  captureProgress = 0;
  captureMessage = 'มองไปที่กล้อง';
  private faceDetectionInterval: ReturnType<typeof setInterval> | null = null;
  private videoStream: MediaStream | null = null;

  constructor(
    private http: HttpClient,
    private timestampService: TimestampService,
    private tokenService: TokenService,
    private employeeService: EmployeeService,
    private comLocationService: CompanyLocationService,
  ) {
    this.companyId = this.tokenService.getSelectCompany().companyId;
  }

  ngOnInit() {
    this.getCurrentLocation();
    faceapi.nets.tinyFaceDetector.loadFromUri('/assets/models/tiny_face_detector');
    faceapi.nets.faceLandmark68Net.loadFromUri('/assets/models/face_landmark_68');
    faceapi.nets.faceRecognitionNet.loadFromUri('/assets/models/face_recognition');
    faceapi.nets.faceExpressionNet.loadFromUri('/assets/models/face_expression');
    this.startVideo();
    this.getCompanyLocation();
  }

  ngOnDestroy() {
    if (this.faceDetectionInterval) {
      clearInterval(this.faceDetectionInterval);
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
    navigator.mediaDevices.getUserMedia({ video: true })
      .then((stream) => {
        this.videoStream = stream;
        this.video.nativeElement.srcObject = stream;
      })
      .catch((err) => {
        console.error('Error accessing camera: ', err);
        this.captureMessage = 'ไม่สามารถเปิดกล้องได้';
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
      if (this.isCapturing) {
        return;
      }

      const detections = await faceapi
        .detectAllFaces(videoEl, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceExpressions();
      const resizedDetections = faceapi.resizeResults(detections, displaySize);

      this.canvas.nativeElement.getContext('2d').clearRect(0, 0, displaySize.width, displaySize.height);
      faceapi.draw.drawDetections(this.canvas.nativeElement, resizedDetections);
      faceapi.draw.drawFaceExpressions(this.canvas.nativeElement, resizedDetections);
      faceapi.draw.drawFaceLandmarks(this.canvas.nativeElement, resizedDetections);

      this.checkMatch = detections.length > 0;
      this.captureMessage = this.checkMatch
        ? 'ตรวจพบใบหน้า พร้อมลงเวลา'
        : 'กรุณาวางใบหน้าให้อยู่กลางจอ';
    }, 200);
  }

  /** Capture multiple frames for InsightFace multi-frame liveness. */
  captureImage(): void {
    if (this.isCapturing || !this.checkMatch) {
      return;
    }

    this.isCapturing = true;
    this.captureProgress = 0;
    this.captureMessage = 'กำลังตรวจ liveness... กรุณาขยับใบหน้าเล็กน้อย';

    const capturedFrames: string[] = [];
    const frameCount = 10;
    const captureIntervalMs = 150;

    const captureProcess = setInterval(() => {
      if (capturedFrames.length >= frameCount) {
        clearInterval(captureProcess);
        this.sendFramesForVerification(capturedFrames);
        return;
      }

      const frame = this.captureFrame();
      capturedFrames.push(frame);
      this.captureProgress = (capturedFrames.length / frameCount) * 100;
    }, captureIntervalMs);
  }

  captureFrame(): string {
    const video = this.video.nativeElement;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || video.width || 640;
    canvas.height = video.videoHeight || video.height || 480;
    const context = canvas.getContext('2d');
    context?.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg');
  }

  sendFramesForVerification(frames: string[]): void {
    this.captureMessage = 'กำลังยืนยันใบหน้า...';
    const formData = new FormData();
    frames.forEach((dataUrl, index) => {
      formData.append('files', this.dataURLtoFile(dataUrl, `frame_${index}.jpg`));
    });

    this.http.post(environment.baseUrl + `/face/members/check-face-emp`, formData).subscribe({
      next: (response: any) => {
        this.memberId = response.memberId;
        this.capturedImage = frames[Math.floor(frames.length / 2)];
        this.captureMessage = 'ยืนยันสำเร็จ กำลังบันทึกลงเวลา';

        this.employeeService.getMemberById(this.companyId, this.memberId).subscribe({
          next: (result) => {
            this.employeeModel = result;
            this.timestampModel = new TimestampModel({
              company_employeeId: this.employeeModel.company_employeeId,
              timestampType: 1,
              latitude: this.location?.latitude,
              longitude: this.location?.longitude,
            });
            this.uploadPhototimestamp();
          },
          error: (error) => {
            swal('Employee Lookup Failed', error.error?.detail || 'ไม่พบข้อมูลพนักงาน', 'error');
            this.resetCaptureState();
          },
        });
      },
      error: (error) => {
        const detail = error.error?.detail || 'Liveness check failed. Please try again.';
        swal('Face Check Failed', detail, 'error');
        this.resetCaptureState();
      },
    });
  }

  uploadPhototimestamp() {
    const file = this.dataURLtoFile(this.capturedImage!, 'face.jpg');
    const formData = new FormData();
    formData.append('file', file);
    this.http.post(environment.baseUrl + `/api/upload-image/`, formData).subscribe({
      next: (response: any) => {
        this.timestampModel.photoTimestamp = response.filename;
        this.saveTimestamp();
      },
      error: (error) => {
        swal('Photo Upload Failed', error.error?.detail || 'Upload failed.', 'error');
        this.resetCaptureState();
      },
    });
  }

  saveTimestamp() {
    if (this.locationArea.length > 0) {
      this.timestampModel.timestampType = 1;
      this.timestampModel.locationName = this.locationArea[0].locationName;
    } else {
      this.timestampModel.timestampType = 0;
    }
    this.timestampService.save(this.companyId, this.timestampModel).subscribe({
      next: (result) => {
        swal(
          result.timestampType == 0 ? 'Warning Location !!' : 'Complete !!',
          'ลงเวลาการทำงาน ' +
            this.employeeModel.getFullname() +
            ' เวลา ' +
            new Date(result.timestamp).toLocaleTimeString('th', { hour: '2-digit', minute: '2-digit' }),
          result.timestampType == 0 ? 'info' : 'success',
        );
        this.resetCaptureState();
      },
      error: (error) => {
        swal('Save Failed', error.error?.detail || 'บันทึกลงเวลาไม่สำเร็จ', 'error');
        this.resetCaptureState();
      },
    });
  }

  resetCaptureState() {
    this.isCapturing = false;
    this.captureProgress = 0;
    this.captureMessage = this.checkMatch
      ? 'ตรวจพบใบหน้า พร้อมลงเวลา'
      : 'กรุณาวางใบหน้าให้อยู่กลางจอ';
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
