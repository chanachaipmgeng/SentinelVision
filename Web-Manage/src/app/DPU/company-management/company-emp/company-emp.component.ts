import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, ElementRef, ViewChild } from '@angular/core';
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
@Component({
  selector: 'app-company-emp',
  standalone: true,
  imports: [SharedModule, NgSelectModule, RouterModule, MaterialModuleModule, TranslateModule, FlatpickrModule, MatDatepickerModule, FormsModule, CommonModule, FileUploadModule],
  providers: [FlatpickrDefaults],
  templateUrl: './company-emp.component.html',
  styleUrl: './company-emp.component.css',
})
export class CompanyEmpComponent {
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
  constructor(private http: HttpClient,private employeeService: EmployeeService, public translate: TranslateService, private departmentService: DepartmentService, private positionService: PositionService, private tokenService: TokenService) {
    this.uploadConfig()
    this.companyId = this.tokenService.getSelectCompany().companyId;
  }

  @ViewChild('video') video: ElementRef;
  @ViewChild('canvas') canvas: ElementRef;
  capturedImage: string | null = null;
  uploadStatus: string = '';
  checkMatch = false;
  memberId = ""
  isFaceDetected = false; // Flag to determine if a face is detected


  initFace() {
    // โหลดโมเดล Face Detection ของ face-api.js
    faceapi.nets.tinyFaceDetector.loadFromUri('/assets/models/tiny_face_detector');
    faceapi.nets.faceLandmark68Net.loadFromUri('/assets/models/face_landmark_68');
    faceapi.nets.faceRecognitionNet.loadFromUri('/assets/models/face_recognition');
    faceapi.nets.faceExpressionNet.loadFromUri('/assets/models/face_expression');
    // เปิดกล้อง
    this.startVideo();
  }

  startVideo(): void {
    console.log("test")
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
      this.http.post(environment.baseUrl + `/face/members/${this.selectModel.member.memberId}/add-face`, formData).subscribe({
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
    this.initFace()
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

  save() {
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
            this.selectModel.companyRoleType = 0
            this.employeeService.save(this.selectModel, this.companyId).subscribe(result => {
              swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
              this.ngOnInit()
              this.childModal?.nativeElement.click()
            })
          } else {
            this.employeeService.update(this.selectModel, this.companyId).subscribe(result => {
              swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
              this.ngOnInit()
              this.childModal?.nativeElement.click()
            })

          }
          // this.selectModel.member.role = 0

        }

      });


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
