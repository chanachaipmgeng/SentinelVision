import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { AuthService } from '../../../shared/services/auth.service';
import swal from 'sweetalert';

@Component({
  selector: 'app-cover',
  standalone: true,
  imports: [SharedModule, CommonModule, RouterModule, FormsModule],
  templateUrl: './cover.component.html',
  styleUrls: ['./cover.component.scss']
})
export class CoverComponent implements OnInit {
  email = '';
  token = '';
  newPassword = '';
  confirmPassword = '';
  busy = false;
  mode: 'request' | 'set' = 'request';

  constructor(
    private auth: AuthService,
    private route: ActivatedRoute,
    private router: Router,
  ) {}

  ngOnInit(): void {
    const q = this.route.snapshot.queryParamMap.get('token') || '';
    if (q.trim()) {
      this.token = q.trim();
      this.mode = 'set';
    }
  }

  resetPass(): void {
    if (this.busy) return;
    const email = (this.email || '').trim();
    if (!email || !email.includes('@')) {
      swal('แจ้งเตือน', 'กรุณากรอกอีเมลให้ถูกต้อง', 'warning');
      return;
    }
    this.busy = true;
    this.auth.sendResetPassword(email).subscribe({
      next: () => {
        this.busy = false;
        swal(
          'ส่งคำขอแล้ว',
          'หากอีเมลนี้มีในระบบ คุณจะได้รับลิงก์รีเซ็ตรหัสผ่าน',
          'success'
        );
      },
      error: () => {
        this.busy = false;
        swal('Error', 'ไม่สามารถส่งคำขอได้ กรุณาลองใหม่', 'error');
      },
    });
  }

  submitNewPassword(): void {
    if (this.busy) return;
    if ((this.newPassword || '').length < 8) {
      swal('แจ้งเตือน', 'รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร', 'warning');
      return;
    }
    if (this.newPassword !== this.confirmPassword) {
      swal('แจ้งเตือน', 'รหัสผ่านยืนยันไม่ตรงกัน', 'warning');
      return;
    }
    this.busy = true;
    this.auth.resetPassword(this.token, this.newPassword).subscribe({
      next: () => {
        this.busy = false;
        swal('สำเร็จ', 'ตั้งรหัสผ่านใหม่แล้ว กรุณาเข้าสู่ระบบ', 'success').then(() => {
          this.router.navigate(['/auth/login']);
        });
      },
      error: (err) => {
        this.busy = false;
        const detail = err?.error?.detail || 'รีเซ็ตรหัสผ่านไม่สำเร็จ';
        swal('Error', detail, 'error');
      },
    });
  }
}
