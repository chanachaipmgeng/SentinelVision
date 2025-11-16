import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { FileItem, FileUploader } from 'ng2-file-upload';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { MemberModel } from 'src/app/shared/models/member.model';
import { GuestService } from 'src/app/shared/services/guest.service';

@Component({
  selector: 'app-signup',
  templateUrl: './signup.component.html',
  styleUrls: ['./signup.component.scss']
})
export class SignupComponent implements OnInit {
  hideUploandImg = true
  pictureUrl = ""

  companyName = ""
  uploader: FileUploader = new FileUploader({})
  profilePhotoFileName = ""
  profilePhotoError = false

  firstName = ""
  lastName = ""
  email = ""
  password = ""
  mobileNumber = ""
  sex = 2
  birthDate = ""
  idCard = ""
  passportNo = ""
  constructor(private guestService: GuestService,
    private modalService: NgbModal,
    private router: Router
  ) {
    this.setUpload()
  }

  ngOnInit(): void {
    var tooltiptriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltiptriggerList.map(function (e) {
      return new bootstrap.Tooltip(e)
    });
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
      this.profilePhotoFileName = ""
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
        this.profilePhotoFileName = ""
        this.profilePhotoError = true
        fileItem.isCancel = true;
        return;
      } else if (fileItem.file.type.indexOf("image") === -1) {
        const modalRef = this.modalService.open(AlertComponent, { centered: true })
        modalRef.componentInstance.message = "please upload image only.";
        this.profilePhotoFileName = ""
        this.profilePhotoError = true
        fileItem.isCancel = true;
        return;
      } else {
        this.profilePhotoError = false
      }
    };
  }

  isUpdateDisabled() {
    if (!this.email ||
      !this.firstName ||
      !this.lastName ||
      !this.password ||
      !this.mobileNumber ||
      this.profilePhotoError) {
      return true
    } else {
      return false
    }
  }
  submit() {
    const modalRef = this.modalService.open(AlertComponent, { centered: true })
    modalRef.componentInstance.message = "Do you want to confirm?"
    modalRef.componentInstance.confirmModal = true
    modalRef.result.then(response => {
      const body = {
        firstName: this.firstName,
        lastName: this.lastName,
        mobileNumber: this.mobileNumber,
        sex: this.sex,
        email: this.email,
        password: this.password,
        birthDate: this.birthDate,
        idCard: this.idCard,
        passportNo: this.passportNo,
        nationality: "",
        profilePhoto: this.profilePhotoFileName.split(",").length == 2 ? this.profilePhotoFileName.split(",")[1] : ""
      }
      this.guestService.checkMail(body).subscribe((checkMail: any) => {
        if (checkMail.success) {
          this.guestService.register(body).subscribe((register: any) => {
            if (register.success) {
              const modalRef = this.modalService.open(AlertComponent, { centered: true })
              modalRef.componentInstance.message = "Registration completed"
              this.router.navigate(['/auth/signin']);
            } else {
               const modalRef = this.modalService.open(AlertComponent, { centered: true })
              modalRef.componentInstance.message = "Unable to register"
              
            }
          }, error => {
            const modalRef = this.modalService.open(AlertComponent, { centered: true })
            modalRef.componentInstance.message = error.message
          })
        } else {
          const modalRef = this.modalService.open(AlertComponent, { centered: true })
          modalRef.componentInstance.message = "Email is Duplicate."
        }
      }, error => {
        const modalRef = this.modalService.open(AlertComponent, { centered: true })
        modalRef.componentInstance.message = error.message
      })
    }, error => {

    })
  }
}