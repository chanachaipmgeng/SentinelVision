import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { UntypedFormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { AuthService } from 'src/app/shared/services/auth.service';
import { ConfigService } from 'src/app/shared/services/config.service';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { NativeMobileService } from 'src/app/shared/services/native-mobile.service';
import { PdpaService } from 'src/app/shared/services/pdpa.service';
import { TokenService } from 'src/app/shared/services/token.service';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-signin',
  templateUrl: './signin.component.html',
  styleUrls: ['./signin.component.scss']
})
export class SigninComponent implements OnInit {

  username = ""
  password = ""
  msg = ""
  PassWord: boolean = false;
  tokenAD = '';

  constructor(
    private fb: UntypedFormBuilder,
    private auth: AuthService,
    private router: Router,
    private tokenService: TokenService,
    private empServie: EmployeeService,
    private configService: ConfigService,
    private route: ActivatedRoute
  ) {
  }

  ngOnInit(): void {
    var tooltiptriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltiptriggerList.map(function (e: any) {
      return new bootstrap.Tooltip(e)
    });

  }


  onSubmit() {
    this.auth
      .login(
        this.username,
        this.password
      ).subscribe(result => {
        this.tokenService.saveToken(result.access_token);
        // this.tokenService.saveRefreshToken(result.refreshToken);
        this.tokenService.saveUser(result);
        if (result.member.status == 1) {
          this.getCompanyList(result.member.memberId)
        } else {
          this.msg = 'ไม่สามารถใช้งานได้กรุณาติดต่อผู้ให้บริการ'
        }
      }, (error: HttpErrorResponse) => {
        this.password = ""
        if (error.status == 403 || error.status == 401) {
          this.msg = "Username or password is incorrect."
        } else {
          this.msg = error.message;
        }
      })
  }

  getCompanyList(memberId: string) {
    this.empServie.getCompanyEmp(memberId).subscribe(result => {
      if (result.length > 0) {
        this.tokenService.saveSelectCompany(result[0]);
        this.router.navigate(["/company/home-company"]);
      }
    }, (error) => {
      this.msg = 'คุณไม่มีสิทธิ์ใช้งานในส่วนนี้ กรุณาติดต่อบริษัทของคุณ';
    })
  }

  showPassWord() {
    this.PassWord = !this.PassWord
  }

}
