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
import { environment } from '../../../environments/environment';
import { playCaptureBeep, playFaceFoundBeep, unlockBeepAudio } from '../../shared/utils/beep';
import { speakText, unlockSpeech } from '../../shared/utils/tts';

type LoginMode = 'password' | 'face';
type FaceScanPhase =
  | 'idle'
  | 'camera'
  | 'identifying'
  | 'greet'
  | 'blink'
  | 'confirming'
  | 'error';

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
  greetName = '';
  greetPictureUrl = '';
  blinkStatus = '';

  nowTime = '';
  nowDate = '';

  @ViewChild('faceVideo') faceVideo?: ElementRef<HTMLVideoElement>;
  @ViewChild('faceVideoMobile') faceVideoMobile?: ElementRef<HTMLVideoElement>;
  @ViewChild('faceCanvas') faceCanvas?: ElementRef<HTMLCanvasElement>;

  private clockTimer?: ReturnType<typeof setInterval>;
  private mediaStream: MediaStream | null = null;
  private pendingFaceFrames: Blob[] | null = null;
  private faceChallengeToken: string | null = null;
  private blinkWatchTimer?: ReturnType<typeof setInterval>;
  private blinkDeadlineTimer?: ReturnType<typeof setTimeout>;
  private blinkBusy = false;
  private blinkConfirming = false;
  private faceDetector: {
    detect: (
      source: HTMLVideoElement,
    ) => Promise<Array<{ boundingBox: { x: number; y: number; width: number; height: number } }>>;
  } | null = null;

  constructor(
    @Inject(DOCUMENT) private document: Document,
    private renderer: Renderer2,
    public tokenService: TokenService,
    private routes: Router,
    private formBuilder: FormBuilder,
    public authService: AuthService,
    private empServie: EmployeeService,
    private translate: TranslateService,
  ) {
    // Drop member session leftovers without wiping unrelated prefs (lang, UI).
    this.tokenService.clearSession();
    this.tokenService.clearKioskSession();
  }

  get faceBusy(): boolean {
    return (
      this.showLoader ||
      this.facePhase === 'identifying' ||
      this.facePhase === 'confirming' ||
      this.facePhase === 'blink'
    );
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
    this.clearFaceChallenge();
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
    this.clearFaceChallenge();
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
    unlockBeepAudio();
    unlockSpeech();
    this.ensureFaceDetector();
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
    if (this.faceBusy && this.facePhase !== 'blink') return;
    this.error = '';
    this.errorMessage = '';

    if (this.mfaRequired && this.faceChallengeToken) {
      this.submitFaceChallenge();
      return;
    }

    if (!this.mediaStream) {
      await this.startCamera();
      if (!this.mediaStream) return;
    }

    this.stopBlinkWatch();
    unlockBeepAudio();
    unlockSpeech();
    this.facePhase = 'identifying';
    this.faceHint =
      this.lang === 'th' ? 'กำลังระบุตัวตน… อยู่นิ่งๆ สักครู่' : 'Identifying… hold still';
    this.showLoader = true;
    this.greetName = '';
    this.greetPictureUrl = '';
    this.blinkStatus = '';
    this.blinkConfirming = false;

    try {
      const frames = await this.captureFrames(3);
      this.authService.identifyWithFace(frames).subscribe({
        next: async (res) => {
          this.showLoader = false;
          this.faceChallengeToken = res.challengeToken;
          this.greetName = res.displayName || (this.lang === 'th' ? 'ผู้ดูแล' : 'Admin');
          this.greetPictureUrl = res.picture
            ? `${environment.baseUrl}/images/${res.picture}`
            : '';
          this.facePhase = 'greet';
          this.faceHint =
            this.lang === 'th'
              ? `สวัสดี, ${this.greetName}`
              : `Welcome, ${this.greetName}`;
          playFaceFoundBeep();
          speakText(
            this.lang === 'th'
              ? `สวัสดี ${this.greetName} กรุณากระพริบตาเพื่อยืนยัน`
              : `Welcome ${this.greetName}. Please blink to confirm.`,
            { lang: this.lang === 'th' ? 'th-TH' : 'en-US', rate: 1 },
          );
          await new Promise((r) => setTimeout(r, 800));
          if (!this.faceChallengeToken || this.loginMode !== 'face') return;
          this.facePhase = 'blink';
          this.faceHint =
            this.lang === 'th' ? 'กระพริบตา 1–2 ครั้งเพื่อเข้าสู่ระบบ' : 'Blink once or twice to sign in';
          this.blinkStatus =
            this.lang === 'th' ? 'รอการกระพริบ…' : 'Waiting for blink…';
          this.startBlinkWatch();
        },
        error: () => {
          this.showLoader = false;
          this.facePhase = 'camera';
          this.clearFaceChallenge();
          this.error =
            this.lang === 'th'
              ? 'ไม่สามารถยืนยันตัวตนได้'
              : 'Could not verify identity';
          this.faceHint =
            this.lang === 'th' ? 'จัดใบหน้าให้อยู่ในกรอบ' : 'Center your face in the frame';
        },
      });
    } catch {
      this.showLoader = false;
      this.facePhase = 'camera';
      this.clearFaceChallenge();
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

  private submitFaceChallenge(): void {
    if (!this.faceChallengeToken) {
      this.facePhase = 'camera';
      this.showLoader = false;
      this.error =
        this.lang === 'th'
          ? 'เซสชันยืนยันหมดอายุ กรุณาสแกนใหม่'
          : 'Challenge expired. Please scan again.';
      return;
    }
    this.showLoader = true;
    this.facePhase = 'confirming';
    this.faceHint =
      this.lang === 'th' ? 'กำลังเข้าสู่ระบบ…' : 'Signing you in…';
    const totpVal = this.loginForm.controls['totpCode']?.value || '';
    this.authService.loginWithFace(totpVal, this.faceChallengeToken).subscribe({
      next: (result) => {
        this.pendingFaceFrames = null;
        this.clearFaceChallenge();
        this.stopCamera();
        this.authService.applyMemberSession(result);
        if (result.mustChangePassword || result.must_change_password) {
          this.routes.navigate(['/auth/change-password']);
          return;
        }
        const role = Number((result as { member?: { role?: unknown; status?: unknown } }).member?.role);
        const status = Number((result as { member?: { role?: unknown; status?: unknown } }).member?.status);
        if (status === 1 && role === 99) {
          this.routes.navigate(['/admin/member-manage']);
          return;
        }
        if (role === 99) {
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
        const detail = err?.error?.detail || '';
        if (detail === 'MFA_REQUIRED') {
          this.mfaRequired = true;
          this.facePhase = 'camera';
          this.error =
            this.lang === 'th'
              ? 'บัญชีนี้เปิดใช้งาน 2FA กรุณากรอกรหัส 6 หลักจากแอป Authenticator'
              : '2FA is enabled. Enter the 6-digit authenticator code.';
          this.faceHint =
            this.lang === 'th'
              ? 'กรอกรหัส 2FA แล้วกดยืนยันอีกครั้ง'
              : 'Enter 2FA then confirm again';
        } else if (detail === 'Invalid 2FA authenticator code') {
          this.mfaRequired = true;
          this.facePhase = 'camera';
          this.error =
            this.lang === 'th'
              ? 'รหัสยืนยันตัวตน 2FA ไม่ถูกต้อง'
              : 'Invalid 2FA authenticator code';
        } else {
          this.pendingFaceFrames = null;
          this.clearFaceChallenge();
          this.facePhase = 'camera';
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

  private clearFaceChallenge(): void {
    this.stopBlinkWatch();
    this.faceChallengeToken = null;
    this.greetName = '';
    this.greetPictureUrl = '';
    this.blinkStatus = '';
    this.blinkConfirming = false;
  }

  private stopBlinkWatch(): void {
    if (this.blinkWatchTimer) {
      clearInterval(this.blinkWatchTimer);
      this.blinkWatchTimer = undefined;
    }
    if (this.blinkDeadlineTimer) {
      clearTimeout(this.blinkDeadlineTimer);
      this.blinkDeadlineTimer = undefined;
    }
    this.blinkBusy = false;
  }

  private ensureFaceDetector(): void {
    if (this.faceDetector) return;
    try {
      const FaceDetectorCtor = (
        globalThis as {
          FaceDetector?: new (opts?: object) => {
            detect: (
              source: HTMLVideoElement,
            ) => Promise<Array<{ boundingBox: { x: number; y: number; width: number; height: number } }>>;
          };
        }
      ).FaceDetector;
      if (typeof FaceDetectorCtor === 'function') {
        this.faceDetector = new FaceDetectorCtor({ fastMode: true, maxDetectedFaces: 1 });
      }
    } catch {
      this.faceDetector = null;
    }
  }

  private startBlinkWatch(): void {
    this.stopBlinkWatch();
    this.ensureFaceDetector();
    const samples: number[] = [];
    let closedAt = 0;
    let sawClosed = false;
    let baseline = 0;
    this.blinkDeadlineTimer = setTimeout(() => {
      if (this.facePhase !== 'blink' || this.blinkConfirming) return;
      this.blinkStatus =
        this.lang === 'th'
          ? 'ยังไม่จับกระพริบ — กระพริบแรงขึ้นอีกครั้ง'
          : 'Blink not detected — blink again clearly';
    }, 15000);

    this.blinkWatchTimer = setInterval(async () => {
      if (this.facePhase !== 'blink' || this.blinkBusy || this.blinkConfirming) return;
      this.blinkBusy = true;
      try {
        const lum = await this.sampleEyeBandLuminance();
        if (lum == null) return;
        samples.push(lum);
        if (samples.length > 36) samples.shift();
        if (samples.length < 4) return;

        if (!baseline || samples.length <= 8) {
          baseline = samples.reduce((a, b) => a + b, 0) / samples.length;
        } else {
          // Slow baseline drift so lighting changes do not lock the gate.
          baseline = baseline * 0.92 + lum * 0.08;
        }

        const prev = samples[samples.length - 2] ?? lum;
        const drop = prev - lum;
        const dipFromBase = baseline > 0 ? (baseline - lum) / baseline : 0;
        // Soft thresholds: phone cameras often only dip a few percent on blink.
        const closed = dipFromBase >= 0.045 || drop >= 4.5 || lum <= baseline * 0.94;
        const reopened =
          sawClosed &&
          lum >= baseline * 0.96 &&
          Date.now() - closedAt >= 60 &&
          Date.now() - closedAt < 1800;

        if (!sawClosed && closed) {
          sawClosed = true;
          closedAt = Date.now();
          this.blinkStatus =
            this.lang === 'th' ? 'ตรวจพบการกระพริบ…' : 'Blink seen…';
        } else if (reopened) {
          await this.completeBlinkChallenge();
        } else if (sawClosed && Date.now() - closedAt > 1800) {
          sawClosed = false;
          closedAt = 0;
          this.blinkStatus =
            this.lang === 'th' ? 'ลองกระพริบอีกครั้ง…' : 'Try blinking again…';
        }
      } finally {
        this.blinkBusy = false;
      }
    }, 70);
  }

  private async completeBlinkChallenge(): Promise<void> {
    if (this.blinkConfirming || this.facePhase !== 'blink' || !this.faceChallengeToken) return;
    this.blinkConfirming = true;
    this.stopBlinkWatch();
    playCaptureBeep();
    this.blinkStatus =
      this.lang === 'th' ? 'ตรวจพบการกระพริบ — กำลังเข้าสู่ระบบ…' : 'Blink detected — signing in…';
    this.faceHint =
      this.lang === 'th' ? 'กำลังเข้าสู่ระบบ…' : 'Signing you in…';
    // No second face capture/GPU match — challenge from identify is enough after blink.
    this.submitFaceChallenge();
  }

  /**
   * Mean luminance of the eye band for a crude blink detector.
   * Login has no JWT yet — FaceDetector when available, else center crop.
   */
  private async sampleEyeBandLuminance(): Promise<number | null> {
    const video = this.activeVideo();
    const canvas = this.faceCanvas?.nativeElement;
    if (!video || !canvas || video.readyState < 2) return null;
    const vw = video.videoWidth || 640;
    const vh = video.videoHeight || 480;
    const targetW = 320;
    const scale = Math.min(1, targetW / vw);
    const w = Math.max(1, Math.round(vw * scale));
    const h = Math.max(1, Math.round(vh * scale));
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, w, h);

    let box: { x: number; y: number; width: number; height: number } | null = null;
    if (this.faceDetector) {
      try {
        const faces = await this.faceDetector.detect(video);
        const b = faces[0]?.boundingBox;
        if (b && b.width > 8 && b.height > 8) {
          const sx = w / (video.videoWidth || w);
          const sy = h / (video.videoHeight || h);
          // Slightly taller eye band for better blink signal.
          box = {
            x: b.x * sx + b.width * sx * 0.12,
            y: b.y * sy + b.height * sy * 0.18,
            width: b.width * sx * 0.76,
            height: b.height * sy * 0.22,
          };
        }
      } catch {
        /* fall through to center crop */
      }
    }

    if (!box) {
      box = { x: w * 0.28, y: h * 0.28, width: w * 0.44, height: h * 0.14 };
    }

    const x = Math.max(0, Math.floor(box.x));
    const y = Math.max(0, Math.floor(box.y));
    const bw = Math.max(1, Math.floor(box.width));
    const bh = Math.max(1, Math.floor(box.height));
    const data = ctx.getImageData(x, y, Math.min(bw, w - x), Math.min(bh, h - y)).data;
    let sum = 0;
    let n = 0;
    for (let i = 0; i < data.length; i += 4) {
      sum += 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
      n += 1;
    }
    return n ? sum / n : null;
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
