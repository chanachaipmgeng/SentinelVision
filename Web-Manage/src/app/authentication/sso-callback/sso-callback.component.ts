import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../shared/services/auth.service';
import { apiErrorMessage } from '../../shared/utils/http-error-body';
import { TokenService } from '../../shared/services/token.service';
import { EmployeeService } from '../../DPU/services/employee.service';
import { UserModel } from '../../shared/user-auth.model';

/**
 * OIDC redirect target (`OIDC_REDIRECT_URI` = `<origin>/auth/sso/callback`).
 * Posts `code` + `state` + the `txn` kept in sessionStorage to the API, then
 * stores tokens through TokenService exactly like the password login does.
 */
@Component({
    selector: 'app-sso-callback',
    imports: [CommonModule, RouterModule],
    template: `
    <div class="min-h-screen flex items-center justify-center p-6">
      <div class="box p-6 w-full max-w-md space-y-3 text-center">
        <h2 class="text-lg font-semibold">เข้าสู่ระบบด้วย SSO</h2>
        @if (!error) {
          <p class="text-sm text-gray-500">กำลังตรวจสอบตัวตนกับผู้ให้บริการ SSO...</p>
        } @else {
          <p class="text-red-600 text-sm">{{ error }}</p>
          <a class="ti-btn ti-btn-primary w-full" routerLink="/auth/login">กลับไปหน้าเข้าสู่ระบบ</a>
        }
      </div>
    </div>
  `
})
export class SsoCallbackComponent implements OnInit {
  error = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService,
    private tokenService: TokenService,
    private empService: EmployeeService
  ) {}

  ngOnInit(): void {
    const q = this.route.snapshot.queryParamMap;
    const idpError = q.get('error');
    if (idpError) {
      this.error = q.get('error_description') || `ผู้ให้บริการ SSO ปฏิเสธการเข้าสู่ระบบ (${idpError})`;
      return;
    }
    const code = q.get('code') || '';
    const state = q.get('state') || '';
    const txn = this.authService.takeSsoTransaction();
    if (!code || !state || !txn || txn.state !== state) {
      this.error = 'ข้อมูลการเข้าสู่ระบบไม่ครบถ้วนหรือหมดอายุ กรุณาลองใหม่อีกครั้ง';
      return;
    }
    this.authService.ssoCallback(code, state, txn.txn).subscribe({
      next: (result) => this.completeLogin(result),
      error: (err: HttpErrorResponse) => {
        this.error = apiErrorMessage(err, 'เข้าสู่ระบบด้วย SSO ไม่สำเร็จ');
      },
    });
  }

  private completeLogin(result: UserModel & { returnTo?: string }): void {
    this.authService.applyMemberSession(result);
    if (result.mustChangePassword || result.must_change_password) {
      this.router.navigate(['/auth/change-password']);
      return;
    }
    if (result.member?.status != 1) {
      this.error = 'ไม่สามารถใช้งานได้กรุณาติดต่อผู้ให้บริการ';
      return;
    }
    if (result.returnTo && typeof result.returnTo === 'string' && result.returnTo.startsWith('/')) {
      this.router.navigateByUrl(result.returnTo);
      return;
    }
    if (result.member.role == 99) {
      this.router.navigate(['/admin/member-manage']);
      return;
    }
    this.empService.getCompanyAdmin(result.member.memberId).subscribe({
      next: (companies) => {
        if (companies?.length > 0) {
          this.router.navigate(['/company/home/' + companies[0].companyId]);
        } else {
          this.error = 'คุณไม่มีสิทธิ์ใช้งานในส่วนนี้';
        }
      },
      error: () => {
        this.error = 'คุณไม่มีสิทธิ์ใช้งานในส่วนนี้';
      },
    });
  }
}
