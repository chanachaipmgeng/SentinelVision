import { Component, input, output } from '@angular/core';

/** Full-viewport electric-blue/cyan aura orb stage for Copilot voice playback. */
@Component({
  selector: 'app-speak-orb',
  standalone: true,
  template: `
    <div class="sv-orb-stage" role="dialog" aria-modal="true" aria-label="AI Voice Stage">
      <div class="sv-orb-backdrop" (click)="stopped.emit()"></div>
      <div class="sv-orb-core" [class.is-speaking]="speaking()">
        <div class="sv-orb-ring sv-orb-ring--1"></div>
        <div class="sv-orb-ring sv-orb-ring--2"></div>
        <div class="sv-orb-sphere"></div>
      </div>
      <div class="sv-orb-caption">
        <div class="sv-orb-label">{{ speaking() ? 'SentinelVision Copilot กำลังพูด...' : 'พร้อมรับฟัง' }}</div>
        @if (excerpt()) {
          <p class="sv-orb-text">{{ excerpt() }}</p>
        }
        <button type="button" class="sv-orb-stop" (click)="stopped.emit()">
          <i class="ri-stop-circle-line"></i>
          <span>หยุดเสียง (Barge-in)</span>
        </button>
      </div>
    </div>
  `,
  styles: [
    `
      .sv-orb-stage {
        position: fixed;
        inset: 0;
        z-index: 1250;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 2rem;
        padding: 1.5rem;
      }
      .sv-orb-backdrop {
        position: absolute;
        inset: 0;
        background: radial-gradient(circle at center, rgba(6, 20, 42, 0.92), rgba(4, 8, 15, 0.96));
        backdrop-filter: blur(18px);
      }
      .sv-orb-core {
        position: relative;
        width: 170px;
        height: 170px;
        display: grid;
        place-items: center;
      }
      .sv-orb-sphere {
        width: 112px;
        height: 112px;
        border-radius: 9999px;
        background: radial-gradient(circle at 35% 30%, #67e8f9, #0ea5e9 45%, #1d4ed8 85%);
        box-shadow:
          0 0 48px rgba(56, 189, 248, 0.65),
          0 0 96px rgba(20, 184, 166, 0.35),
          inset 0 0 24px rgba(255, 255, 255, 0.45);
        transition: transform 0.25s ease;
      }
      .sv-orb-core.is-speaking .sv-orb-sphere {
        animation: sv-orb-pulse 1.3s ease-in-out infinite;
      }
      .sv-orb-ring {
        position: absolute;
        inset: 0;
        border-radius: 9999px;
        border: 1px solid rgba(56, 189, 248, 0.35);
      }
      .sv-orb-ring--1 {
        animation: sv-orb-spin 7s linear infinite;
      }
      .sv-orb-ring--2 {
        inset: -16px;
        border-color: rgba(20, 184, 166, 0.28);
        border-style: dashed;
        animation: sv-orb-spin 11s linear infinite reverse;
      }
      .sv-orb-caption {
        position: relative;
        max-width: 34rem;
        text-align: center;
        color: #f1f5f9;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.75rem;
      }
      .sv-orb-label {
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #67e8f9;
      }
      .sv-orb-text {
        margin: 0;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #cbd5e1;
        max-height: 8rem;
        overflow: hidden;
      }
      .sv-orb-stop {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.55rem 1.2rem;
        border-radius: 9999px;
        border: 1px solid rgba(244, 63, 94, 0.45);
        background: rgba(244, 63, 94, 0.16);
        color: #fecdd3;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
      }
      @keyframes sv-orb-pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
      }
      @keyframes sv-orb-spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }
    `,
  ],
})
export class SpeakOrbComponent {
  readonly speaking = input(false);
  readonly excerpt = input('');
  readonly stopped = output<void>();
}
