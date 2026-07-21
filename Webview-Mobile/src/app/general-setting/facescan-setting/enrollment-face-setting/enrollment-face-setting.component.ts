import { HttpClient } from '@angular/common/http';
import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import * as faceapi from 'face-api.js';
import { TokenService } from 'src/app/shared/services/token.service';
import { environment } from 'src/environments/environment';
import swal from 'sweetalert';
import { assetUrl } from 'src/app/shared/utils/asset-url';

@Component({
  selector: 'app-enrollment-face-setting',
  templateUrl: './enrollment-face-setting.component.html',
  styleUrls: ['./enrollment-face-setting.component.css']
})
export class EnrollmentFaceSettingComponent {
  @ViewChild('video') video: ElementRef;
  @ViewChild('canvas') canvas: ElementRef;
  capturedImage: string | null = null;
  uploadStatus: string = '';
  checkMatch = false;
  memberId = ""
  isFaceDetected = false; // Flag to determine if a face is detected
  constructor(private http: HttpClient, private tokenService: TokenService) {
    this.memberId = this.tokenService.getUser().member.memberId;
  }

  ngOnInit() {
    const modelsBase = assetUrl('assets/models');
    faceapi.nets.tinyFaceDetector.loadFromUri(`${modelsBase}/tiny_face_detector`);
    faceapi.nets.faceLandmark68Net.loadFromUri(`${modelsBase}/face_landmark_68`);
    faceapi.nets.faceRecognitionNet.loadFromUri(`${modelsBase}/face_recognition`);
    faceapi.nets.faceExpressionNet.loadFromUri(`${modelsBase}/face_expression`);
    this.startVideo();
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
      const detections = await faceapi.detectAllFaces(videoEl, new faceapi.TinyFaceDetectorOptions()).withFaceLandmarks().withFaceExpressions();
      const resizedDetections = faceapi.resizeResults(detections, displaySize);

      // Clear the canvas
      this.canvas.nativeElement.getContext('2d').clearRect(0, 0, displaySize.width, displaySize.height);

      // Draw detections
      faceapi.draw.drawDetections(this.canvas.nativeElement, resizedDetections);
      faceapi.draw.drawFaceExpressions(this.canvas.nativeElement, resizedDetections);
      faceapi.draw.drawFaceLandmarks(this.canvas.nativeElement, resizedDetections);

      // Check if at least one face is detected
      this.isFaceDetected = detections.length > 0;
      this.checkMatch = this.isFaceDetected;
    }, 500);
  }

  // @ViewChild('video') videoElement!: ElementRef;
  // @ViewChild('canvas') canvasElement!: ElementRef;
  // capturedImage: string | null = null;
  // uploadStatus: string = '';

  // constructor(private http: HttpClient) {}

  // ngOnInit(): void {
  //   this.startCamera();
  // }

  // // เริ่มการทำงานของกล้อง
  // startCamera(): void {
  //   navigator.mediaDevices.getUserMedia({ video: true })
  //     .then(stream => {
  //       this.videoElement.nativeElement.srcObject = stream;
  //     })
  //     .catch(err => {
  //       console.error('Error accessing camera: ', err);
  //     });
  // }

  // // แคปเจอร์ภาพจากกล้อง
  captureImage(): void {
    const video = this.video.nativeElement;
    const canvas = this.canvas.nativeElement;
    const context = canvas.getContext('2d');

    // วาดภาพจาก video ลงใน canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    // แปลงภาพใน canvas เป็น base64
    this.capturedImage = canvas.toDataURL('image/jpeg');
    this.uploadImage()
  }

  // // อัปโหลดภาพที่แคปเจอร์แล้ว
  uploadImage(): void {
    if (this.capturedImage) {
      // แปลง Base64 เป็นไฟล์
      const file = this.dataURLtoFile(this.capturedImage, 'face.jpg');
      const formData = new FormData();
      formData.append('file', file);

      // ส่งคำร้อง HTTP POST ไปยัง backend
      this.http.post(environment.baseUrl + `/face/members/${this.memberId}/add-face`, formData).subscribe({
        next: (response: any) => {
          this.uploadStatus = 'Face uploaded successfully!';
          swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
        },
        error: (error) => {
          this.uploadStatus = 'Error uploading face!';
          console.error('Error:', error);
        }
      });
    }
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
}
