import { Component, Inject, OnDestroy, OnInit, Renderer2 } from '@angular/core';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ToastrService } from 'ngx-toastr';
import { CommonModule, DOCUMENT } from '@angular/common';
import { SharedModule } from '../../shared/shared.module';
import { Router, RouterModule } from '@angular/router';
import { TokenService } from '../../shared/services/token.service';
import { AuthService } from '../../shared/services/auth.service';
import { LoginModel } from '../../shared/user-auth.model';
import { HttpClientModule } from '@angular/common/http';
import { Validators } from 'ngx-editor';
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
  }

  ngOnInit(): void {
    this.loginForm = this.formBuilder.group({
      username: ['', Validators.required],
      password: ['', Validators.required],
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
    const body: LoginModel = new LoginModel();
    body.username = this.username;
    body.password = this.password;
    this.authService
      .login(this.loginForm.controls['username'].value, this.loginForm.controls['password'].value)
      .subscribe(
        (result) => {
          this.tokenService.saveToken(result.access_token);
          this.tokenService.saveUser(result);
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
        () => {
          this.showLoader = false;
          this.error = 'Username หรือ Password ไม่ถูกต้อง';
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
