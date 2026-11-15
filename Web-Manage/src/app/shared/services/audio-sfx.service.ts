import { Injectable, signal } from '@angular/core';

const SFX_PREF_KEY = 'dpu.uiSfxEnabled';

/** Subtle Web Audio UI sound effects for SentinelVision Console & Kiosk. */
@Injectable({ providedIn: 'root' })
export class AudioSfxService {
  private audioCtx: AudioContext | null = null;
  readonly enabled = signal<boolean>(this.loadPref());

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('pointerdown', () => this.initContext(), { once: true, passive: true });
    }
  }

  toggle(): void {
    const next = !this.enabled();
    this.enabled.set(next);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(SFX_PREF_KEY, next ? '1' : '0');
    }
    if (next) {
      this.playTick();
    }
  }

  private loadPref(): boolean {
    if (typeof localStorage === 'undefined') {
      return true;
    }
    return localStorage.getItem(SFX_PREF_KEY) !== '0';
  }

  private initContext(): AudioContext | null {
    if (typeof window === 'undefined') {
      return null;
    }
    const AC =
      window.AudioContext ||
      (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) {
      return null;
    }
    if (!this.audioCtx) {
      this.audioCtx = new AC();
    }
    if (this.audioCtx.state === 'suspended') {
      void this.audioCtx.resume();
    }
    return this.audioCtx;
  }

  /** Subtle tactile tick for hover/focus/tab switches. */
  playTick(): void {
    if (!this.enabled()) return;
    const ctx = this.initContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(820, now);
    osc.frequency.exponentialRampToValueAtTime(140, now + 0.045);

    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.linearRampToValueAtTime(0.04, now + 0.008);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.045);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.05);
  }

  /** Crisp cyber beep for HUD actions / Kiosk mode switches. */
  playBeep(): void {
    if (!this.enabled()) return;
    const ctx = this.initContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(660, now);
    osc.frequency.exponentialRampToValueAtTime(990, now + 0.07);

    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.linearRampToValueAtTime(0.06, now + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.09);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.1);
  }

  /** Warm dual-tone chime for completed actions. */
  playChime(): void {
    if (!this.enabled()) return;
    const ctx = this.initContext();
    if (!ctx) return;

    const notes = [587.33, 880];
    notes.forEach((freq, idx) => {
      const start = ctx.currentTime + idx * 0.075;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, start);
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.linearRampToValueAtTime(0.055, start + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.16);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.18);
    });
  }
}
