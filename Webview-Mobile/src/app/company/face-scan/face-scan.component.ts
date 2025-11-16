import { Component, ViewChild, ElementRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
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
@Component({
  selector: 'app-face-scan',
  standalone: true,
  imports: [
    CommonModule,
  ],
  templateUrl: './face-scan.component.html',
  styleUrls: ['./face-scan.component.css'],
})
export class FaceScanComponent {
  @ViewChild('video') video: ElementRef;
  @ViewChild('canvas') canvas: ElementRef;
  locationList: CompanyLocationModel[] = []
  locationArea: CompanyLocationModel[] = []
  capturedImage: string | null = null;
  uploadStatus: string = '';
  checkMatch = false;
  companyId = ""
  memberId = ""
  timestampModel: TimestampModel = new TimestampModel()
  employeeModel: EmployeeModel = new EmployeeModel()
  location: { latitude: number; longitude: number } = { latitude: 0, longitude: 0 };
  errorMessage: string | null = null;
  detectMS = 300;
  blinkCount = 0;
  lastBlinkTime = 0;
  depthThreshold = -0.1; // ค่าความลึกขั้นต่ำของใบหน้า (ป้องกันภาพนิ่ง)
  constructor(private http: HttpClient, private timestampService: TimestampService, private tokenService: TokenService, private employeeService: EmployeeService, private comLocationService: CompanyLocationService) {
    this.companyId = this.tokenService.getSelectCompany().companyId;
    this.memberId = this.tokenService.getUser().member.memberId;
    this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.memberId).subscribe(result => {
      this.employeeModel = result
      this.timestampModel = new TimestampModel({
        "company_employeeId": this.employeeModel.company_employeeId,
        "timestampType": 1,
        "latitude": 0,
        "longitude": 0,
      })
    })
  }

  ngOnInit() {
    // this.getCurrentLocation()
    // โหลดโมเดล Face Detection ของ face-api.js
    faceapi.nets.tinyFaceDetector.loadFromUri('/assets/models/tiny_face_detector');
    faceapi.nets.faceLandmark68Net.loadFromUri('/assets/models/face_landmark_68');
    faceapi.nets.faceRecognitionNet.loadFromUri('/assets/models/face_recognition');
    faceapi.nets.faceExpressionNet.loadFromUri('/assets/models/face_expression');
    // เปิดกล้อง
    this.startVideo();
    this.getCompanyLocation()
  }

  getCompanyLocation() {
    this.comLocationService.getLists(this.companyId).subscribe(result => {
      this.locationList = result
      this.getCurrentLocation()
    })
  }



  startVideo(): void {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        this.video.nativeElement.srcObject = stream;
      })
      .catch(err => {
        console.error('Error accessing camera: ', err);
      });
  }

  // ตรวจจับใบหน้าและวาดกรอบครอบใบหน้า
  async detectFace() {
    const videoEl = this.video.nativeElement;
    const displaySize = { width: videoEl.width, height: videoEl.height };
    faceapi.matchDimensions(this.canvas.nativeElement, displaySize);

    setInterval(async () => {
      const detections = await faceapi.detectSingleFace(videoEl, new faceapi.TinyFaceDetectorOptions()).withFaceLandmarks().withFaceExpressions()
      if (detections) {
        const resizedDetections = faceapi.resizeResults(detections, displaySize);

        // ล้าง canvas ก่อนวาดใหม่
        this.canvas.nativeElement.getContext('2d').clearRect(0, 0, displaySize.width, displaySize.height);

        // วาดกรอบครอบใบหน้าลงบน canvas
        faceapi.draw.drawDetections(this.canvas.nativeElement, resizedDetections!);
        faceapi.draw.drawFaceExpressions(this.canvas.nativeElement, resizedDetections!);
        faceapi.draw.drawFaceLandmarks(this.canvas.nativeElement, resizedDetections!);

        this.checkMatch = true
        this.detectBlink(detections)
      } else {
        this.checkMatch = false
        this.blinkCount = 1;
      }

    }, 100);  // ตรวจจับทุกๆ 100ms
  }

  /** คำนวณ Eye Aspect Ratio (EAR) */
  calculateEAR(eye: any) {
    const A = this.getDistanceBetween(eye[1], eye[5]);
    const B = this.getDistanceBetween(eye[2], eye[4]);
    const C = this.getDistanceBetween(eye[0], eye[3]);

    return (A + B) / (2.0 * C);
  }

  /** คำนวณระยะห่างระหว่างจุด */
  getDistanceBetween(p1: any, p2: any) {
    return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
  }

  detectBlink(detection: any) {
    const landmarks = detection.landmarks;
    const leftEye = landmarks.getLeftEye();
    const rightEye = landmarks.getRightEye();

    const leftEAR = this.calculateEAR(leftEye);
    const rightEAR = this.calculateEAR(rightEye);
    const avgEAR = (leftEAR + rightEAR) / 2.0;

    console.log("EAR:", avgEAR.toFixed(2)); // Debugging

    if (avgEAR <= 0.25) {
      if (Date.now() - this.lastBlinkTime > 1000) {  // ป้องกันการตรวจซ้ำบ่อยเกินไป
        this.blinkCount++;
        this.lastBlinkTime = Date.now();
        console.log("Blink Detected:", this.blinkCount);

        // ✅ กะพริบตา 2 ครั้งเพื่อ Capture รูป
        if (this.blinkCount >= 2) {
          this.captureImage();
          this.blinkCount = 0;  // Reset นับใหม่
        }
      }
    }

    // if (this.blinkCount == 3) {
    //   console.log("✅ Blink Detected - Capturing Image...");
    //   // Reset Blink Count
    //   this.captureImage();
    //   // this.blinkCount++;
    // }
  }
  // // แคปเจอร์ภาพจากกล้อง
  captureImage(): void {
    // this.detectMS = 2000;
    const video = this.video.nativeElement;
    const canvas = this.canvas.nativeElement;
    const context = canvas.getContext('2d');

    // วาดภาพจาก video ลงใน canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    // แปลงภาพใน canvas เป็น base64
    this.capturedImage = canvas.toDataURL('image/jpeg');
    // console.log(this.capturedImage)
    // this.uploadImage() checkface
    this.uploadImage()
  }

  // // อัปโหลดภาพที่แคปเจอร์แล้ว
  uploadImage(): void {
    if (this.capturedImage) {
      const file = this.dataURLtoFile(this.capturedImage, 'face.jpg');
      const formData = new FormData();
      formData.append('file', file);

      this.http.post(environment.baseUrl + `/face/members/${this.memberId}/check-face`, formData).subscribe({
        next: (response: any) => {
          this.uploadPhototimestamp();
        },
        error: (error) => {
          swal("Face Check Failed", this.uploadStatus, "error");
        }
      });
    }
  }

  uploadPhototimestamp() {
    const base64ImagePayload = {
      base64_image: this.capturedImage // Ensure `capturedImage` includes the full base64 string (e.g., "data:image/png;base64,...")
    };
    const file = this.dataURLtoFile(this.capturedImage!, 'face.jpg');
    const formData = new FormData();
    formData.append('file', file);
    this.http.post(environment.baseUrl + `/api/upload-image/`, formData).subscribe({
      next: (response: any) => {
        console.log('Upload successful:', response);
        this.timestampModel.photoTimestamp = response.filename
        this.saveTimestamp()
      },
      error: (error) => {
        console.error('Error uploading image:', error);
        alert('Error: ' + error.error.detail || 'Upload failed.');
      }
    });
  }

  saveTimestamp() {
    if (this.locationArea.length > 0) {
      this.timestampModel.timestampType = 1
      this.timestampModel.locationName = this.locationArea[0].locationName
    } else {
      this.timestampModel.timestampType = 0
    }
    this.timestampModel.latitude = this.location?.latitude
    this.timestampModel.longitude = this.location?.longitude
    this.timestampService.save(this.companyId, this.timestampModel).subscribe(result => {
      swal(result.timestampType == 0 ? "Warning Location !!" : "Complete !!", "ลงเวลาการทำงาน " + this.employeeModel.getFullname() + " เวลา " + new Date(result.timestamp).toLocaleTimeString("th", { hour: '2-digit', minute: '2-digit' }), result.timestampType == 0 ? "info" : "success").then((isOk: any) => {
        console.log(isOk)
        if (isOk) {
          this.blinkCount = 0;
        }
      });
    })
  }


  // // แปลง Base64 เป็นไฟล์ (Blob)
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
          this.searchCompanyLocation()
          this.errorMessage = null; // Clear any previous errors
          console.log('Location fetched successfully:', this.location);
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
        }
      );

    } else {
      this.errorMessage = 'Geolocation is not supported by this browser.';
    }
  }

  private toRad(value: number): number {
    return (value * Math.PI) / 180;
  }

  getDistance(lat1: string, lon1: string, lat2: string, lon2: string): number {
    const R = 6371; // รัศมีของโลกในหน่วยกิโลเมตร
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
    console.log("locationArea", this.locationArea)
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
