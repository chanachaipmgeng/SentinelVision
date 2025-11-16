import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslateService } from '@ngx-translate/core';
import { FileItem, FileUploader, ParsedResponseHeaders } from 'ng2-file-upload';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { MemberService } from 'src/app/shared/services/member.service';
import { TokenService } from 'src/app/shared/services/token.service';
import { environment } from 'src/environments/environment';
import swal from 'sweetalert';

@Component({
  selector: 'app-personal-info',
  templateUrl: './personal-info.component.html',
  styleUrls: ['./personal-info.component.scss'],
})
export class PersonalInfoComponent implements OnInit {
  hideUploandImg = false
  personalModel: EmployeeModel
  bossModel: EmployeeModel
  memberId: string = ""
  uploaderProfile: FileUploader;
  uploadErrorMsg: string = "";
  companyId = ""
  constructor(private employeeService: EmployeeService,
    private route: ActivatedRoute,
    private modalService: NgbModal,
    public translate: TranslateService,
    private tokenService: TokenService) {
    this.memberId = this.route.snapshot.paramMap.get('memberId')!
    this.companyId = this.tokenService.getSelectCompany().companyId;
    this.uploadConfig()
    this.getEmpProfile()
  }

  ngOnInit() {
  }

  getEmpProfile() {
    this.employeeService.getMemberById(this.companyId, this.memberId).subscribe(result => {
      this.personalModel = result
      this.getBossEmpProfile()
    })
  }

  getBossEmpProfile() {
    this.employeeService.getMemberById(this.companyId, this.personalModel.bossId).subscribe(result => {
      this.bossModel = result
      console.log("boss",this.bossModel)
    })
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
        this.personalModel.member.picture = res.filename
        swal(res.message, "บันทึกสำเร็จ", "success");

      } else {
        this.uploadErrorMsg = "cannot upload file.";
        swal("Opp!!", "ไม่สามารถอัพโหลดได้", "info");
      }
    };
  }

  // setUpload() {
  //   this.uploader.onAfterAddingFile = (fileItem: FileItem) => {
  //     fileItem.withCredentials = false;
  //     while (this.uploader.queue.length > 1) {
  //       this.uploader.queue[0].remove();
  //     }
  //     if (fileItem.file.size > 5000000) {
  //       const modalRef = this.modalService.open(AlertComponent, { centered: true })
  //       modalRef.componentInstance.message = "maximum file size 5mb.";
  //       this.profilePhotoFileName = this.personalModel.getPicture() ? this.personalModel.getPicture() : ""
  //       this.profilePhotoNewFile = false
  //       this.profilePhotoError = true
  //       fileItem.isCancel = true;
  //       return;
  //     } else if (fileItem.file.type.indexOf("image") === -1) {
  //       const modalRef = this.modalService.open(AlertComponent, { centered: true })
  //       modalRef.componentInstance.message = "please upload image only.";
  //       this.profilePhotoFileName = this.personalModel.getPicture() ? this.personalModel.getPicture() : ""
  //       this.profilePhotoNewFile = false
  //       this.profilePhotoError = true
  //       fileItem.isCancel = true;
  //       return;
  //     } else {
  //       this.profilePhotoNewFile = true
  //       this.profilePhotoError = false
  //     }
  //   };
  // }

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
          this.employeeService.update(this.personalModel, this.companyId).subscribe(result => {
            swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
            this.ngOnInit()
          })
        }

      });
  }

  // submit() {
  //   const modalRef = this.modalService.open(AlertComponent, { centered: true })
  //   modalRef.componentInstance.message = "Do you want to confirm?"
  //   modalRef.componentInstance.confirmModal = true
  //   modalRef.result.then(respone => {
  //     const body = {
  //       memberId: this.personalModel.member.memberId!,
  //       companyId: this.tokenService.getSelectCompany().companyId,
  //       employeeCode: this.personalModel.company_employeeId!,
  //       pictureData: this.profilePhotoFileName.split(",")[1]
  //     }
  //   }, error => {

  //   })
  // }
  // async loadData() {
  // if (this.memberId) {
  //   try {
  //     const data = await this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.memberId).toPromise();
  //     this.personalModel = data
  //     this.personalModel.birthday = this.personalModel ? (this.personalModel.birthday ? this.personalModel.birthday.split("-").reverse().join("/") : "-") : "-"
  //     this.personalModel.startwork = this.personalModel ? (this.personalModel.startwork ? this.personalModel.startwork.split("-").reverse().join("/") : "-") : "-"
  //     this.calculateAge();
  //     this.profilePhotoFileName = this.personalModel.getPicture() ? this.personalModel.getPicture() : ""
  //   } catch (error) {
  //     console.error('Error loading data:', error);
  //   }
  // } else {
  //   try {
  //     const data = await this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.tokenService.getUser().member.memberId).toPromise();
  //     this.personalModel = data
  //     this.personalModel.birthday = this.personalModel ? (this.personalModel.birthday ? this.personalModel.birthday.split("-").reverse().join("/") : "-") : "-"
  //     this.personalModel.startwork = this.personalModel ? (this.personalModel.startwork ? this.personalModel.startwork.split("-").reverse().join("/") : "-") : "-"
  //     // this.calculateAge();
  //     this.profilePhotoFileName = this.personalModel.getPicture() ? this.personalModel.getPicture() : ""
  //   } catch (error) {
  //     console.error('Error loading data:', error);
  //   }
  // }
  // }

}
