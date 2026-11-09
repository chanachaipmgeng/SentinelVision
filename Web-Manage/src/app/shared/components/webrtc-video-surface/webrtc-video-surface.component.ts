import {
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Same-origin WHEP player for MediaMTX (Phase 3 live wall).
 * Expects ``whepUrl`` like ``/mediamtx/{path}/whep``.
 */
@Component({
  selector: 'app-webrtc-video-surface',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="sv-webrtc" [class.sv-webrtc--error]="!!error">
      <video #video playsinline autoplay muted [attr.aria-label]="label || 'Live camera'"></video>
      <div class="sv-webrtc__status" *ngIf="status && !error">{{ status }}</div>
      <div class="sv-webrtc__error" *ngIf="error" role="alert">{{ error }}</div>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
        width: 100%;
        height: 100%;
      }
      .sv-webrtc {
        position: relative;
        width: 100%;
        height: 100%;
        background: #0b1220;
        overflow: hidden;
      }
      video {
        width: 100%;
        height: 100%;
        object-fit: contain;
        background: #0b1220;
      }
      .sv-webrtc__status,
      .sv-webrtc__error {
        position: absolute;
        inset: auto 0 0 0;
        padding: 0.4rem 0.6rem;
        font-size: 0.75rem;
        color: #e2e8f0;
        background: rgb(15 23 42 / 0.65);
      }
      .sv-webrtc__error {
        color: #fecaca;
      }
    `,
  ],
})
export class WebrtcVideoSurfaceComponent implements OnChanges, OnDestroy {
  @Input() whepUrl = '';
  @Input() label = '';
  @ViewChild('video', { static: true }) videoRef!: ElementRef<HTMLVideoElement>;

  status = '';
  error = '';

  private pc: RTCPeerConnection | null = null;
  private aborted = false;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['whepUrl']) {
      void this.restart();
    }
  }

  ngOnDestroy(): void {
    this.aborted = true;
    this.teardown();
  }

  private async restart(): Promise<void> {
    this.teardown();
    this.aborted = false;
    this.error = '';
    this.status = '';
    const url = (this.whepUrl || '').trim();
    if (!url) return;
    this.status = 'Connecting…';
    try {
      await this.connect(url);
      if (!this.aborted) this.status = '';
    } catch (err) {
      if (this.aborted) return;
      this.error = err instanceof Error ? err.message : 'WebRTC failed';
      this.status = '';
    }
  }

  private async connect(url: string): Promise<void> {
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    });
    this.pc = pc;
    pc.addTransceiver('video', { direction: 'recvonly' });
    pc.addTransceiver('audio', { direction: 'recvonly' });
    pc.ontrack = (ev) => {
      const video = this.videoRef?.nativeElement;
      if (!video) return;
      if (video.srcObject !== ev.streams[0]) {
        video.srcObject = ev.streams[0];
        void video.play().catch(() => undefined);
      }
    };

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    await this.waitIceGathering(pc);

    const local = pc.localDescription?.sdp;
    if (!local) throw new Error('No local SDP');

    let lastErr: unknown;
    for (let attempt = 0; attempt < 8; attempt++) {
      if (this.aborted) return;
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/sdp' },
          body: local,
        });
        if (!res.ok) {
          throw new Error(`WHEP ${res.status}`);
        }
        const answer = await res.text();
        await pc.setRemoteDescription({ type: 'answer', sdp: answer });
        return;
      } catch (err) {
        lastErr = err;
        await new Promise((r) => setTimeout(r, 400 + attempt * 200));
      }
    }
    throw lastErr instanceof Error ? lastErr : new Error('WHEP connect failed');
  }

  private waitIceGathering(pc: RTCPeerConnection): Promise<void> {
    if (pc.iceGatheringState === 'complete') return Promise.resolve();
    return new Promise((resolve) => {
      const onChange = () => {
        if (pc.iceGatheringState === 'complete') {
          pc.removeEventListener('icegatheringstatechange', onChange);
          resolve();
        }
      };
      pc.addEventListener('icegatheringstatechange', onChange);
      setTimeout(() => {
        pc.removeEventListener('icegatheringstatechange', onChange);
        resolve();
      }, 2500);
    });
  }

  private teardown(): void {
    if (this.pc) {
      try {
        this.pc.close();
      } catch {
        /* ignore */
      }
      this.pc = null;
    }
    const video = this.videoRef?.nativeElement;
    if (video) {
      video.srcObject = null;
    }
  }
}
