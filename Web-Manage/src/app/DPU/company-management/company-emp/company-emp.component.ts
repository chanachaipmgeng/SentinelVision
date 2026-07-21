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
  private modelsLoaded = false;
  private faceDetectionInterval: ReturnType<typeof setInterval> | null = null;
  private videoStream: MediaStream | null = null;
  private readonly bodyModalIds = ['modal-face', 'modal-detail', 'modal-face-management'];
  private movedModalNodes: HTMLElement[] = [];

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
    this.checkMatch = false;
    this.isFaceDetected = false;
    this.faceStatus = 'กำลังโหลดโมเดลและกล้อง...';
    this.cdr.detectChanges();

    try {
      await this.ensureFaceModels();
      await this.startVideo();
      this.faceStatus = 'วางใบหน้าให้อยู่กลางจอ';
      this.cdr.detectChanges();
      // Wait a tick so video element binds stream before detection loop
      setTimeout(() => this.detectFace(), 300);
    } catch (err: any) {
      console.error(err);
      this.faceStatus = err?.message || 'เปิดกล้องไม่สำเร็จ';
      this.cdr.detectChanges();
    }
  }

  private async ensureFaceModels(): Promise<void> {
    if (this.modelsLoaded) {
      return;
    }
    await Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri('/assets/models/tiny_face_detector'),
      faceapi.nets.faceLandmark68Net.loadFromUri('/assets/models/face_landmark_68'),
      faceapi.nets.faceRecognitionNet.loadFromUri('/assets/models/face_recognition'),
      faceapi.nets.faceExpressionNet.loadFromUri('/assets/models/face_expression'),
    ]);
    this.modelsLoaded = true;
  }

  startVideo(): Promise<void> {
    this.stopFaceCamera();
    return navigator.mediaDevices.getUserMedia({ video: true }).then((stream) => {
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
      if (!videoEl.srcObject || videoEl.readyState < 2) {
        return;
      }
      try {
        const detections = await faceapi
          .detectAllFaces(videoEl, new faceapi.TinyFaceDetectorOptions())
          .withFaceLandmarks()
          .withFaceExpressions();
        const resizedDetections = faceapi.resizeResults(detections, displaySize);
        const ctx = this.canvas.nativeElement.getContext('2d');
        ctx.clearRect(0, 0, displaySize.width, displaySize.height);
        faceapi.draw.drawDetections(this.canvas.nativeElement, resizedDetections);
        faceapi.draw.drawFaceExpressions(this.canvas.nativeElement, resizedDetections);
        faceapi.draw.drawFaceLandmarks(this.canvas.nativeElement, resizedDetections);

        this.ngZone.run(() => {
          this.isFaceDetected = detections.length > 0;
          this.checkMatch = this.isFaceDetected;
          this.faceStatus = this.checkMatch
            ? 'ตรวจพบใบหน้า พร้อมบันทึก'
            : 'กรุณาวางใบหน้าให้อยู่กลางจอ';
          this.cdr.detectChanges();
        });
      } catch (e) {
        console.error('detectFace error', e);
      }
    }, 400);
  }

  captureImage(): void {
    if (this.isUploadingFace) {
      return;
    }
    if (!this.selectModel?.member?.memberId) {
      swal('Error', 'ไม่พบข้อมูลพนักงาน', 'error');
      return;
    }

    const video = this.video.nativeElement;
    const captureCanvas = document.createElement('canvas');
    captureCanvas.width = video.videoWidth || video.width || 640;
    captureCanvas.height = video.videoHeight || video.height || 480;
    const context = captureCanvas.getContext('2d');
    if (!context) {
      swal('Error', 'ไม่สามารถจับภาพจากกล้องได้', 'error');
      return;
    }
    context.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
    this.capturedImage = captureCanvas.toDataURL('image/jpeg');
    this.uploadImage();
  }

  uploadImage(): void {
    if (!this.capturedImage) {
      return;
    }
    const file = this.dataURLtoFile(this.capturedImage, 'face.jpg');
    const formData = new FormData();
    formData.append('file', file);

    this.isUploadingFace = true;
    this.faceStatus = 'กำลังบันทึกใบหน้า...';
    this.http.post(environment.baseUrl + `/face/members/${this.selectModel.member.memberId}/add-face`, formData).subscribe({
      next: () => {
        this.isUploadingFace = false;
        this.uploadStatus = 'Face uploaded successfully!';
        this.faceStatus = 'บันทึกใบหน้าสำเร็จ';
        this.cdr.detectChanges();
        swal('Save Success!!', 'บันทึกข้อมูลสำเร็จ', 'success');
        this.childModalFace?.nativeElement.click();
        this.stopFaceCamera();
      },
      error: (error) => {
        this.isUploadingFace = false;
        this.uploadStatus = 'Error uploading face!';
        const detail = error?.error?.detail || 'บันทึกใบหน้าไม่สำเร็จ';
        this.faceStatus = detail;
        this.cdr.detectChanges();
        console.error('Error:', error);
        swal('Upload Failed', detail, 'error');
      }
    });
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
