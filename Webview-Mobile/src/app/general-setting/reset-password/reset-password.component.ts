import { Component, ContentChild, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { MemberService } from 'src/app/shared/services/member.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-reset-password',
  templateUrl: './reset-password.component.html',
  styleUrls: ['./reset-password.component.css'],
})
export class ResetPasswordComponent implements OnInit {

  // oldPassword = ""
  // newPassword = ""
  // confirmNewPassword = ""
  oldPassword: string = ""
  newPassword: string = ""
  confirmNewPassword: string = ""
  showOldPassWord: boolean = false;
  showNewPassWord: boolean = false;
  showConfirmPass: boolean = false;
  checkOPeror = false

  constructor(
    private tokenService: TokenService,
    private memberService: MemberService,
    private modalService: NgbModal,
    public activatedRoute: ActivatedRoute,
    private router: Router
  ) { }

  ngOnInit() { }

  OnSubmit() {
    const body = { memberId: this.tokenService.getUser().member.memberId, oldPassword: this.oldPassword, newPassword: this.newPassword };

    const modalRef = this.modalService.open(AlertComponent, { centered: true })
    modalRef.componentInstance.message = "Do you want to confirm?"
    modalRef.componentInstance.confirmModal = true
    modalRef.result.then(respone => {
      this.memberService.changePassword(body).subscribe((result: any) => {
        if (result.success) {
          const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
          modalAlertRef.componentInstance.message = "STATUS.Success"
          this.router.navigate(['/general']);
        } else {
          this.checkOPeror = true;
          this.oldPassword = ""
          this.newPassword = ""
          this.confirmNewPassword = ""
        }
      }, error => {
        const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
        modalAlertRef.componentInstance.message = "STATUS.Fail"
      })
    })
  }

  isChangePasswordDisabled() {
    if (!this.oldPassword || !this.newPassword || !this.confirmNewPassword || this.confirmNewPassword != this.newPassword ) {
      return true
    } else {
      return false
    }
  }

  showPassWord(buttonName: string){
    if(buttonName == "old"){
      this.showOldPassWord = !this.showOldPassWord;
    }
    if(buttonName == "new"){
      this.showNewPassWord = !this.showNewPassWord;
    }
    if(buttonName == "confirm"){
      this.showConfirmPass = !this.showConfirmPass;
    }
  }


}
