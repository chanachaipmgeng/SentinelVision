import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { TokenService } from '../../../shared/services/token.service';
import { AuthService } from '../../../shared/services/auth.service';
import swal from 'sweetalert';

@Component({
  selector: 'app-profile-security',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule, PageToolbarComponent],
  templateUrl: './profile-security.component.html',
  styleUrls: ['../../../shared/styles/dpu-list-page.css'],
  encapsulation: ViewEncapsulation.None,
})
export class ProfileSecurityComponent implements OnInit {
  username = '';
  email = '';
  mfa = { totpEnabled: false, oidcConfigured: false };
  setup?: { secret: string; otpauthUri: string };
  mfaCode = '';
  pw = { currentPassword: '', newPassword: '', confirm: '' };
  busy = false;

  constructor(
    private http: HttpClient,
    private token: TokenService,
    private auth: AuthService
  ) {
    const user = this.token.getUser();
    this.username = user?.member?.username || '';
    this.email = user?.member?.email || '';
  }

  ngOnInit(): void {
    this.reloadMfa();
  }

  reloadMfa(): void {
    this.http.get<any>('/auth/mfa/status').subscribe({
      next: (s) => (this.mfa = { ...this.mfa, ...s }),
      error: () => undefined,
    });
  }

  changePassword(): void {
    if (this.pw.newPassword.length < 8) {
      swal('แจ้งเตือน', 'รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร', 'warning');
      return;
    }
    if (this.pw.newPassword !== this.pw.confirm) {
      swal('แจ้งเตือน', 'รหัสผ่านยืนยันไม่ตรงกัน', 'warning');
      return;
    }
    this.busy = true;
    this.http
      .post('/auth/change-password', {
        currentPassword: this.pw.currentPassword,
        newPassword: this.pw.newPassword,
      })
      .subscribe({
        next: () => {
          this.busy = false;
          this.pw = { currentPassword: '', newPassword: '', confirm: '' };
          swal('สำเร็จ', 'เปลี่ยนรหัสผ่านแล้ว', 'success');
        },
        error: (err) => {
          this.busy = false;
          swal('Error', err?.error?.detail || 'เปลี่ยนรหัสผ่านไม่สำเร็จ', 'error');
        },
      });
  }

  startMfa(): void {
    this.http.post<any>('/auth/mfa/setup', {}).subscribe({
      next: (s) => (this.setup = s),
      error: (err) => swal('Error', err?.error?.detail || 'เริ่มตั้งค่า MFA ไม่สำเร็จ', 'error'),
    });
  }

  enableMfa(): void {
    this.http.post('/auth/mfa/enable', { code: this.mfaCode }).subscribe({
      next: () => {
        this.setup = undefined;
        this.mfaCode = '';
        this.reloadMfa();
        swal('สำเร็จ', 'เปิดใช้งาน 2FA แล้ว', 'success');
      },
      error: (err) => swal('Error', err?.error?.detail || 'รหัสไม่ถูกต้อง', 'error'),
    });
  }

  disableMfa(): void {
    this.http.post('/auth/mfa/disable', {}).subscribe({
      next: () => {
        this.reloadMfa();
        swal('สำเร็จ', 'ปิด 2FA แล้ว', 'success');
      },
      error: (err) => swal('Error', err?.error?.detail || 'ปิด MFA ไม่สำเร็จ', 'error'),
    });
  }

  logoutEverywhere(): void {
    this.auth.logout(this.token.getRefreshToken()).subscribe({
      next: () => this.token.signOut(),
      error: () => this.token.signOut(),
    });
  }
}
