import {
  Component,
  ElementRef,
  Inject,
  OnDestroy,
  OnInit,
  Renderer2,
  ViewChild,
} from '@angular/core';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ToastrService } from 'ngx-toastr';
import { CommonModule, DOCUMENT } from '@angular/common';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { SharedModule } from '../../shared/shared.module';
import { Router, RouterModule } from '@angular/router';
import { TokenService } from '../../shared/services/token.service';
import { AuthService } from '../../shared/services/auth.service';
import { LoginModel } from '../../shared/user-auth.model';
import { EmployeeService } from '../../DPU/services/employee.service';

type LoginMode = 'password' | 'face';
type FaceScanPhase = 'idle' | 'camera' | 'scanning' | 'error';

@Component({
    selector: 'app-login',
    imports: [SharedModule, CommonModule, RouterModule, FormsModule, ReactiveFormsModule, TranslateModule],
    providers: [AuthService, { provide: ToastrService, useClass: ToastrService }],
    templateUrl: './login.component.html',
    styleUrl: './login.component.scss'
})
export class LoginComponent implements OnInit, OnDestroy {
  lang = 'th';
  username = '';
  password = '';
  totpCode = '';
  mfaRequired = false;
  ssoEnabled = false;
  ssoBusy = false;
  errorMessage = '';
  showLoader = false;
  _error: { name: string; message: string } = { name: '', message: '' };
  public error: unknown = '';
  public loginForm!: FormGroup;

  loginMode: LoginMode = 'password';
  facePhase: FaceScanPhase = 'idle';
  faceHint = '';
  cameraError = '';

  nowTime = '';
  nowDate = '';

  @ViewChild('faceVideo') faceVideo?: ElementRef<HTMLVideoElement>;
  @ViewChild('faceVideoMobile') faceVideoMobile?: ElementRef<HTMLVideoElement>;
  @ViewChild('faceCanvas') faceCanvas?: ElementRef<HTMLCanvasElement>;

  private clockTimer?: ReturnType<typeof setInterval>;
  private mediaStream: MediaStream | null = null;
  private pendingFaceFrames: Blob[] | null = null;

  constructor(
    @Inject(DOCUMENT) private document: Document,
    private renderer: Renderer2,
    public tokenService: TokenService,
    private routes: Router,
    private formBuilder: FormBuilder,
    public authService: AuthService,
    private empServie: EmployeeService,
    private translate: TranslateService
  ) {
    localStorage.clear();
    this.tokenService.clearKioskSession();
  }

  ngOnInit(): void {
    this.lang = this.translate.currentLang || this.translate.defaultLang || localStorage.getItem('sv_lang') || 'th';
    this.loginForm = this.formBuilder.group({
      username: ['', Validators.required],
      password: ['', Validators.required],
      totpCode: [''],
    });
    this.renderer.addClass(this.document.body, 'dpu-login-body');
    this.authService.ssoStatus().subscribe({
      next: (s) => (this.ssoEnabled = !!s?.enabled),
      error: () => (this.ssoEnabled = false),
    });
    this.tickClock();
    this.clockTimer = setInterval(() => this.tickClock(), 1000);
  }

  setLang(code: string): void {
    this.lang = code;
    this.translate.use(code);
    try {
      localStorage.setItem('sv_lang', code);
    } catch {}
  }

  ngOnDestroy(): void {
    this.renderer.removeClass(this.document.body, 'dpu-login-body');
    if (this.clockTimer) {
      clearInterval(this.clockTimer);
      this.clockTimer = undefined;
    }
    this.stopCamera();
  }

  showPassword = false;
  toggleClass = 'off-line';
  toggleVisibility() {
    this.showPassword = !this.showPassword;
    this.toggleClass = this.toggleClass === 'off-line' ? 'line' : 'off-line';
  }

  setLoginMode(mode: LoginMode): void {
    if (this.loginMode === mode) return;
    this.error = '';
    this.errorMessage = '';
    this.mfaRequired = false;
    this.pendingFaceFrames = null;
    this.loginMode = mode;
    if (mode === 'face') {
      void this.startCamera();
    } else {
      this.stopCamera();
      this.facePhase = 'idle';
      this.cameraError = '';
      this.faceHint = '';
    }
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
          // AuthService.login already applied memory access + CSRF; refresh is httpOnly cookie.
          this.authService.applyMemberSession(result);
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

  async startCamera(): Promise<void> {
    this.cameraError = '';
    this.faceHint = this.lang === 'th' ? 'จัดใบหน้าให้อยู่ในกรอบ' : 'Center your face in the frame';
    this.facePhase = 'camera';
    this.stopCamera();
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('no_media');
      }
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: 'user',
          width: { ideal: 640 },
          height: { ideal: 480 },
        },
      });
      this.bindStreamToVideos();
    } catch {
      this.facePhase = 'error';
      this.cameraError =
        this.lang === 'th'
          ? 'ไม่สามารถเปิดกล้องได้ กรุณาอนุญาตการใช้กล้องแล้วลองใหม่'
          : 'Camera unavailable. Allow camera access and try again.';
      this.faceHint = '';
    }
  }

  async scanFaceLogin(): Promise<void> {
    if (this.showLoader || this.facePhase === 'scanning') return;
    this.error = '';
    this.errorMessage = '';

    if (this.mfaRequired && this.pendingFaceFrames?.length) {
      this.submitFaceFrames(this.pendingFaceFrames);
      return;
    }

    if (!this.mediaStream) {
      await this.startCamera();
      if (!this.mediaStream) return;
    }

    this.facePhase = 'scanning';
    this.faceHint = this.lang === 'th' ? 'กำลังสแกน… อยู่นิ่งๆ สักครู่' : 'Scanning… hold still';
    this.showLoader = true;

    try {
      const frames = await this.captureFrames(5);
      this.pendingFaceFrames = frames;
      this.submitFaceFrames(frames);
    } catch {
      this.showLoader = false;
      this.facePhase = 'camera';
      this.error =
        this.lang === 'th'
          ? 'จับภาพใบหน้าไม่สำเร็จ กรุณาลองใหม่'
          : 'Could not capture face frames. Try again.';
      this.faceHint = this.lang === 'th' ? 'จัดใบหน้าให้อยู่ในกรอบ' : 'Center your face in the frame';
    }
  }

  loginWithSso() {
    this.ssoBusy = true;
    this.error = '';
    this.authService.ssoStart().subscribe({
      next: (start) => {
        this.authService.saveSsoTransaction(start);
        window.location.assign(start.authorizeUrl);
      },
      error: (err) => {
        this.ssoBusy = false;
        this.error = err?.error?.detail || 'ไม่สามารถเริ่มการเข้าสู่ระบบด้วย SSO ได้';
      },
    });
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

  private submitFaceFrames(frames: Blob[]): void {
    this.showLoader = true;
    const totpVal = this.loginForm.controls['totpCode']?.value || '';
    this.authService.loginWithFace(frames, totpVal).subscribe({
      next: (result) => {
        this.pendingFaceFrames = null;
        this.stopCamera();
        this.authService.applyMemberSession(result);
        if (result.mustChangePassword || result.must_change_password) {
          this.routes.navigate(['/auth/change-password']);
          return;
        }
        if (result.member?.status == 1 && result.member?.role == 99) {
          this.routes.navigate(['/admin/member-manage']);
          return;
        }
        this.showLoader = false;
        this.facePhase = 'camera';
        this.error =
          this.lang === 'th'
            ? 'ไม่สามารถยืนยันตัวตนได้'
            : 'Could not verify identity';
      },
      error: (err) => {
        this.showLoader = false;
        this.facePhase = 'camera';
        const detail = err?.error?.detail || '';
        if (detail === 'MFA_REQUIRED') {
          this.mfaRequired = true;
          this.error =
            this.lang === 'th'
              ? 'บัญชีนี้เปิดใช้งาน 2FA กรุณากรอกรหัส 6 หลักจากแอป Authenticator'
              : '2FA is enabled. Enter the 6-digit authenticator code.';
          this.faceHint =
            this.lang === 'th'
              ? 'กรอกรหัส 2FA แล้วกดสแกนอีกครั้ง'
              : 'Enter 2FA then scan again';
        } else if (detail === 'Invalid 2FA authenticator code') {
          this.mfaRequired = true;
          this.error =
            this.lang === 'th'
              ? 'รหัสยืนยันตัวตน 2FA ไม่ถูกต้อง'
              : 'Invalid 2FA authenticator code';
        } else {
          this.pendingFaceFrames = null;
          this.error =
            this.lang === 'th'
              ? 'ไม่สามารถยืนยันตัวตนได้'
              : 'Could not verify identity';
          this.faceHint =
            this.lang === 'th' ? 'จัดใบหน้าให้อยู่ในกรอบ' : 'Center your face in the frame';
        }
      },
    });
  }

  private bindStreamToVideos(): void {
    const stream = this.mediaStream;
    if (!stream) return;
    // Wait a tick so @if face mode videos exist in the DOM.
    setTimeout(() => {
      for (const ref of [this.faceVideo, this.faceVideoMobile]) {
        const el = ref?.nativeElement;
        if (!el) continue;
        el.srcObject = stream;
        el.muted = true;
        el.playsInline = true;
        void el.play().catch(() => undefined);
      }
    }, 0);
  }

  private activeVideo(): HTMLVideoElement | null {
    const desktop = this.faceVideo?.nativeElement;
    const mobile = this.faceVideoMobile?.nativeElement;
    if (desktop && desktop.readyState >= 2 && desktop.videoWidth > 0) return desktop;
    if (mobile && mobile.readyState >= 2 && mobile.videoWidth > 0) return mobile;
    return desktop || mobile || null;
  }

  private async captureFrames(count: number): Promise<Blob[]> {
    const video = this.activeVideo();
    const canvas = this.faceCanvas?.nativeElement;
    if (!video || !canvas) {
      throw new Error('camera_not_ready');
    }
    // Ensure first frame is available.
    if (video.readyState < 2) {
      await new Promise<void>((resolve, reject) => {
        const t = setTimeout(() => reject(new Error('video_timeout')), 4000);
        video.addEventListener(
          'loadeddata',
          () => {
            clearTimeout(t);
            resolve();
          },
          { once: true }
        );
      });
    }

    const frames: Blob[] = [];
    for (let i = 0; i < count; i++) {
      const blob = await this.grabJpeg(video, canvas);
      frames.push(blob);
      if (i < count - 1) {
        await new Promise((r) => setTimeout(r, 180));
      }
    }
    return frames;
  }

  private grabJpeg(video: HTMLVideoElement, canvas: HTMLCanvasElement): Promise<Blob> {
    const maxW = 640;
    const vw = video.videoWidth || 640;
    const vh = video.videoHeight || 480;
    const scale = vw > maxW ? maxW / vw : 1;
    const w = Math.max(1, Math.round(vw * scale));
    const h = Math.max(1, Math.round(vh * scale));
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return Promise.reject(new Error('no_canvas'));
    }
    ctx.drawImage(video, 0, 0, w, h);
    return new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob);
          else reject(new Error('toBlob_failed'));
        },
        'image/jpeg',
        0.85
      );
    });
  }

  private stopCamera(): void {
    if (this.mediaStream) {
      for (const track of this.mediaStream.getTracks()) {
        track.stop();
      }
      this.mediaStream = null;
    }
    for (const ref of [this.faceVideo, this.faceVideoMobile]) {
      const el = ref?.nativeElement;
      if (el) {
        el.srcObject = null;
      }
    }
  }

  private tickClock(): void {
    const now = new Date();
    this.nowTime = now.toLocaleTimeString('th-TH', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
    this.nowDate = now.toLocaleDateString('th-TH', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
    });
  }
}
