import { Component, Inject, OnDestroy, OnInit, Renderer2 } from '@angular/core';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ToastrService } from 'ngx-toastr';
import { CommonModule, DOCUMENT } from '@angular/common';
import { SharedModule } from '../../shared/shared.module';
import { Router, RouterModule } from '@angular/router';
import { TokenService } from '../../shared/services/token.service';
import { AuthService } from '../../shared/services/auth.service';
import { LoginModel } from '../../shared/user-auth.model';
import { HttpClientModule } from '@angular/common/http';
import { EmployeeService } from '../../DPU/services/employee.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [SharedModule, CommonModule, RouterModule, FormsModule, HttpClientModule, ReactiveFormsModule],
  providers: [AuthService, { provide: ToastrService, useClass: ToastrService }],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent implements OnInit, OnDestroy {
  username = '';
  password = '';
  totpCode = '';
  mfaRequired = false;
  errorMessage = '';
  showLoader = false;
  _error: { name: string; message: string } = { name: '', message: '' };
  public error: any = '';
  public loginForm!: FormGroup;

  readonly clockTicks = Array.from({ length: 60 }, (_, i) => i);
  nowTime = '';
  nowDate = '';
  hourDeg = 0;
  minuteDeg = 0;
  secondDeg = 0;

  private clockTimer?: ReturnType<typeof setInterval>;

  constructor(
    @Inject(DOCUMENT) private document: Document,
    private renderer: Renderer2,
    public tokenService: TokenService,
    private routes: Router,
    private formBuilder: FormBuilder,
    public authService: AuthService,
    private empServie: EmployeeService
  ) {
    localStorage.clear();
    this.tokenService.clearKioskSession();
  }

  ngOnInit(): void {
    this.loginForm = this.formBuilder.group({
      username: ['', Validators.required],
      password: ['', Validators.required],
      totpCode: [''],
    });
    this.renderer.addClass(this.document.body, 'dpu-login-body');
    this.tickClock();
    this.clockTimer = setInterval(() => this.tickClock(), 250);
  }

  ngOnDestroy(): void {
    this.renderer.removeClass(this.document.body, 'dpu-login-body');
    if (this.clockTimer) {
      clearInterval(this.clockTimer);
      this.clockTimer = undefined;
    }
  }

  showPassword = false;
  toggleClass = 'off-line';
  toggleVisibility() {
    this.showPassword = !this.showPassword;
    this.toggleClass = this.toggleClass === 'off-line' ? 'line' : 'off-line';
  }

  login() {
    this.showLoader = true;
    this.error = '';
    const body: LoginModel = new LoginModel();
    body.username = this.username;
    body.password = this.password;
    const totpVal = this.loginForm.controls['totpCode']?.value || '';
    this.authService
      .login(
        this.loginForm.controls['username'].value,
        this.loginForm.controls['password'].value,
        totpVal
      )
      .subscribe(
        (result) => {
          this.tokenService.saveToken(result.access_token || result.accessToken || '');
          const refresh = result.refresh_token || result.refreshToken;
          if (refresh) {
            this.tokenService.saveRefreshToken(refresh);
          }
          this.tokenService.saveUser(result);
          if (result.mustChangePassword || result.must_change_password) {
            this.routes.navigate(['/auth/change-password']);
            return;
          }
          if (result.member.status == 1) {
            if (result.member.role == 99) {
              this.routes.navigate(['/admin/member-manage']);
            } else {
              this.adminCompanyList(result.member.memberId);
            }
          } else {
            this.error = 'ไม่สามารถใช้งานได้กรุณาติดต่อผู้ให้บริการ';
            this.showLoader = false;
          }
        },
        (err) => {
          this.showLoader = false;
          const detail = err?.error?.detail || '';
          if (detail === 'MFA_REQUIRED') {
            this.mfaRequired = true;
            this.error = 'บัญชีนี้เปิดใช้งาน 2FA กรุณากรอกรหัส 6 หลักจากแอป Authenticator';
          } else if (detail === 'Invalid 2FA authenticator code') {
            this.mfaRequired = true;
            this.error = 'รหัสยืนยันตัวตน 2FA ไม่ถูกต้อง';
          } else {
            this.error = 'Username หรือ Password ไม่ถูกต้อง';
          }
        }
      );
  }

  adminCompanyList(memberId: string) {
    this.empServie.getCompanyAdmin(memberId).subscribe(
      (result) => {
        if (result.length > 0) {
          this.routes.navigate(['/company/home/' + result[0].companyId]);
        } else {
          this.showLoader = false;
          this.error = 'คุณไม่มีสิทธิ์ใช้งานในส่วนนี้';
        }
      },
      () => {
        this.showLoader = false;
        this.error = 'คุณไม่มีสิทธิ์ใช้งานในส่วนนี้';
      }
    );
  }

  private tickClock(): void {
    const now = new Date();
    const ms = now.getMilliseconds() / 1000;
    const s = now.getSeconds() + ms;
    const m = now.getMinutes() + s / 60;
    const h = (now.getHours() % 12) + m / 60;
    this.secondDeg = s * 6;
    this.minuteDeg = m * 6;
    this.hourDeg = h * 30;
    this.nowTime = now.toLocaleTimeString('th-TH', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
    this.nowDate = now.toLocaleDateString('th-TH', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  }
}
