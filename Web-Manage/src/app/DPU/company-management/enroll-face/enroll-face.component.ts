import { HttpClient } from '@angular/common/http';
import { Component, ElementRef, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
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
export class EnrollFaceComponent {
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
  constructor(private http: HttpClient, private timestampService: TimestampService, private tokenService: TokenService, private employeeService: EmployeeService, private comLocationService: CompanyLocationService) {
    this.companyId = this.tokenService.getSelectCompany().companyId;
    // this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.memberId).subscribe(result => {
    //   this.employeeModel = result

    // })
  }

  ngOnInit() {
    this.getCurrentLocation()
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
      const detections = await faceapi.detectAllFaces(videoEl, new faceapi.TinyFaceDetectorOptions()).withFaceLandmarks().withFaceExpressions()
      const resizedDetections = faceapi.resizeResults(detections, displaySize);

      // ล้าง canvas ก่อนวาดใหม่
      this.canvas.nativeElement.getContext('2d').clearRect(0, 0, displaySize.width, displaySize.height);

      // วาดกรอบครอบใบหน้าลงบน canvas
      faceapi.draw.drawDetections(this.canvas.nativeElement, resizedDetections);
      faceapi.draw.drawFaceExpressions(this.canvas.nativeElement, resizedDetections);
      faceapi.draw.drawFaceLandmarks(this.canvas.nativeElement, resizedDetections);

      if (detections.length > 0) {
        this.checkMatch = true
      } else {
        this.checkMatch = false
      }
    }, 100);  // ตรวจจับทุกๆ 100ms
  }

  // // แคปเจอร์ภาพจากกล้อง
  captureImage(): void {
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

      this.http.post(environment.baseUrl + `/face/members/check-face-emp`, formData).subscribe({
        next: (response: any) => {
          this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, response.message).subscribe(result => {
            this.employeeModel = result
            this.timestampModel = new TimestampModel({
              "company_employeeId": this.employeeModel.company_employeeId,
              "timestampType": 1,
              "latitude": this.location?.latitude,
              "longitude": this.location?.longitude
            })
            this.uploadPhototimestamp();
          })

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
    this.timestampService.save(this.companyId, this.timestampModel).subscribe(result => {
      swal(result.timestampType == 0 ? "Warning Location !!" : "Complete !!", "ลงเวลาการทำงาน " + this.employeeModel.getFullname() + " เวลา "+ new Date(result.timestamp).toLocaleTimeString("th", { hour: '2-digit', minute: '2-digit' }), result.timestampType == 0 ? "info" : "success");
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
