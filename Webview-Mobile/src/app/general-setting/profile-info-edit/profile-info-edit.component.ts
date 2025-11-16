import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { FileItem, FileUploader, ParsedResponseHeaders } from 'ng2-file-upload';
import { Subscription, forkJoin } from 'rxjs';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { MemberModel } from 'src/app/shared/models/member.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { MemberService } from 'src/app/shared/services/member.service';
import { TokenService } from 'src/app/shared/services/token.service';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-profile-info-edit',
  templateUrl: './profile-info-edit.component.html',
  styleUrls: ['./profile-info-edit.component.scss'],

})
export class ProfileInfoEditComponent {
  hideUploandImg = true
  memberModel: EmployeeModel = new EmployeeModel()
  pictureUrl = ""
  fullName = ""
  companyName = ""
  uploader: FileUploader = new FileUploader({})
  profilePhotoFileName = ""
  profilePhotoError = false
  constructor(private routes: Router,
    private tokenService: TokenService,
    private modalService: NgbModal,
    private memberService: EmployeeService,
    private router: Router
  ) {
    this.setUpload()
  }

  ngOnInit() {
    this.getProfileInfoEdit()
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      if (reader.result) {
        this.profilePhotoFileName = reader.result.toString()
      }
    };
  }

  showHideUploandImg() {
    this.hideUploandImg = !this.hideUploandImg
    if (this.hideUploandImg) {
      this.profilePhotoFileName = this.memberModel.member.picture
    }
  }
  setUpload() {
    this.uploader.onAfterAddingFile = (fileItem: FileItem) => {
      fileItem.withCredentials = false;
      while (this.uploader.queue.length > 1) {
        this.uploader.queue[0].remove();
      }
      if (fileItem.file.size > 5000000) {
        const modalRef = this.modalService.open(AlertComponent, { centered: true })
        modalRef.componentInstance.message = "maximum file size 5mb.";
        this.profilePhotoFileName = this.memberModel.member.picture
        this.profilePhotoError = true
        fileItem.isCancel = true;
        return;
      } else if (fileItem.file.type.indexOf("image") === -1) {
        const modalRef = this.modalService.open(AlertComponent, { centered: true })
        modalRef.componentInstance.message = "please upload image only.";
        this.profilePhotoFileName = this.memberModel.member.picture
        this.profilePhotoError = true
        fileItem.isCancel = true;
        return;
      } else {
        this.profilePhotoError = false
      }
    };
  }

  getProfileInfoEdit() {
    this.memberService.getById(this.tokenService.getUser().member.memberId, this.tokenService.getSelectCompany().companyId).subscribe(result => {
      this.memberModel = result
      this.profilePhotoFileName = this.memberModel.member.picture
    })
  }

  updateProfilenfoEdit() {
    // if (this.profilePhotoFileName.split(",").length == 2) {
    //   const body = {
    //     memberId: this.tokenService.getUser().member.memberId,
    //     photoData: this.profilePhotoFileName.split(",")[1]
    //   }
    //   forkJoin({
    //     updatePersonalInfo: this.memberService.updatePersonalInfo(this.memberModel),
    //     updatePictureProfile: this.memberService.updatePictureProfile(body)
    //   }).subscribe((result: any) => {
    //     this.hideUploandImg = true
    //     const modalRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalRef.componentInstance.message = "STATUS.Success"
    //   }, error => {
    //     const modalRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalRef.componentInstance.message = "STATUS.Fail"
    //   })
    // } else {
    //   this.memberService.update(this.memberModel, this.tokenService.getSelectCompany().companyId).subscribe((result: any) => {
    //     this.hideUploandImg = true
    //     const modalRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalRef.componentInstance.message = "STATUS.Success"
    //     this.router.navigate(['/general']);
    //   }, error => {
    //     const modalRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalRef.componentInstance.message = "STATUS.Fail"
    //   })
    // }
  }

  isUpdateDisabled() {
    if (!this.memberModel.member.email || !this.memberModel.member.firstName || !this.memberModel.member.lastName || !this.memberModel.member.phoneNumber || this.memberModel.member.picture) {
      return true
    } else {
      return false
    }
  }
  submit() {
    const modalRef = this.modalService.open(AlertComponent, { centered: true })
    modalRef.componentInstance.message = "Do you want to confirm?"
    modalRef.componentInstance.confirmModal = true
    modalRef.result.then(respone => {
      this.updateProfilenfoEdit()
    }, error => {

    })
  }

}
