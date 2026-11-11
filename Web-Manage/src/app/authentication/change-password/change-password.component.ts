import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TokenService } from '../../shared/services/token.service';

@Component({
    selector: 'app-change-password',
    imports: [CommonModule, FormsModule],
    template: `
    <div class="min-h-screen flex items-center justify-center p-6">
      <form class="box p-6 w-full max-w-md space-y-3" (ngSubmit)="submit()">
        <h2 class="text-lg font-semibold">ตั้งรหัสผ่านใหม่</h2>
        <p class="text-sm text-gray-500">รหัสผ่านชั่วคราวใช้ได้ครั้งเดียว กรุณาตั้งรหัสผ่านใหม่อย่างน้อย 8 ตัวอักษร</p>
        <input class="form-control w-full" type="password" name="current" placeholder="รหัสผ่านปัจจุบัน" [(ngModel)]="current" required />
        <input class="form-control w-full" type="password" name="next" placeholder="รหัสผ่านใหม่" [(ngModel)]="next" minlength="8" required />
        <input class="form-control w-full" type="password" name="confirm" placeholder="ยืนยันรหัสผ่านใหม่" [(ngModel)]="confirm" required />
        <p class="text-red-600 text-sm" *ngIf="error">{{ error }}</p>
        <button class="ti-btn ti-btn-primary w-full" type="submit" [disabled]="busy">บันทึก</button>
      </form>
    </div>
  `
})
export class ChangePasswordComponent {
  current = '';
  next = '';
  confirm = '';
  error = '';
  busy = false;

  constructor(private http: HttpClient, private router: Router, private tokenService: TokenService) {}

  submit(): void {
    this.error = '';
    if (this.next.length < 8) {
      this.error = 'รหัสผ่านใหม่ต้องยาวอย่างน้อย 8 ตัวอักษร';
      return;
    }
    if (this.next !== this.confirm) {
      this.error = 'รหัสผ่านใหม่ไม่ตรงกัน';
      return;
    }
    this.busy = true;
    this.http
      .post('/auth/change-password', { currentPassword: this.current, newPassword: this.next })
      .subscribe({
        next: () => {
          this.busy = false;
          const role = this.tokenService.getUser()?.member?.role;
          this.router.navigate([role == 99 ? '/admin/member-manage' : '/company/dashboard']);
        },
        error: (err) => {
          this.busy = false;
          this.error = err?.error?.detail || 'เปลี่ยนรหัสผ่านไม่สำเร็จ';
        },
      });
  }
}
