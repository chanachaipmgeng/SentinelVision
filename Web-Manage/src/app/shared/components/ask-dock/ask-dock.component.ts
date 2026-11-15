import { CommonModule } from '@angular/common';
import { Component, OnDestroy, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AudioSfxService } from '../../services/audio-sfx.service';
import { SileroVadService } from '../../services/silero-vad.service';
import { TokenService } from '../../services/token.service';
import { SpeakOrbComponent } from '../speak-orb/speak-orb.component';

interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

@Component({
  selector: 'app-ask-dock',
  standalone: true,
  imports: [CommonModule, FormsModule, SpeakOrbComponent],
  template: `
    <button
      type="button"
      class="sv-ask-fab"
      (click)="toggleOpen()"
      [attr.aria-expanded]="open()"
      aria-label="Open SentinelVision AI Copilot"
      title="SentinelVision AI Copilot"
    >
      <i class="ri-sparkling-2-line"></i>
      <span>Ask AI</span>
    </button>

    @if (open()) {
      <aside class="sv-ask-dock" aria-label="SentinelVision AI Copilot">
        <header class="sv-ask-dock__header">
          <div class="flex items-center gap-2">
            <span class="sv-ask-dock__dot"></span>
            <div>
              <div class="text-sm font-bold text-slate-100">SentinelVision Copilot</div>
              <div class="text-[11px] text-slate-400">Company-scoped Security &amp; HR Assistant</div>
            </div>
          </div>
          <button type="button" class="sv-ask-dock__close" (click)="open.set(false)" aria-label="Close">
            <i class="ri-close-line"></i>
          </button>
        </header>

        <div class="sv-ask-dock__chips">
          @for (prompt of quickPrompts; track prompt) {
            <button type="button" class="sv-ask-chip" (click)="ask(prompt)">{{ prompt }}</button>
          }
        </div>

        <div class="sv-ask-dock__messages">
          @if (!messages().length) {
            <div class="text-xs text-slate-400 p-3 rounded-xl bg-white/5 border border-white/10">
              ถามสถานะลงเวลาวันนี้ เหตุการณ์ Watchlist/Access Control กล้องออฟไลน์ หรือกดปุ่มไมค์เพื่อสั่งงานด้วยเสียงได้เลยครับ
            </div>
          }
          @for (msg of messages(); track $index) {
            <div class="sv-ask-msg" [class.is-user]="msg.role === 'user'">
              <div class="sv-ask-msg__bubble">{{ msg.content }}</div>
              @if (msg.role === 'assistant' && msg.content) {
                <button type="button" class="sv-ask-speak-btn" (click)="speak(msg.content)" title="อ่านออกเสียง">
                  <i class="ri-volume-up-line"></i>
                  <span>Speak</span>
                </button>
              }
            </div>
          }
          @if (statusLabel()) {
            <div class="text-[11px] text-cyan-300 px-1">{{ statusLabel() }}</div>
          }
        </div>

        <form class="sv-ask-dock__form" (ngSubmit)="submit()">
          <button
            type="button"
            class="sv-ask-mic"
            [class.is-listening]="listening()"
            (click)="toggleVoice()"
            [title]="listening() ? 'หยุดฟัง' : 'พูดคำถาม (Silero VAD)'"
          >
            <i [class]="listening() ? 'ri-mic-fill' : 'ri-mic-line'"></i>
          </button>
          <input
            type="text"
            class="sv-ask-input"
            [(ngModel)]="draft"
            name="draft"
            placeholder="ถาม Copilot เกี่ยวกับระบบวันนี้..."
            [disabled]="streaming()"
          />
          <button type="submit" class="sv-ask-send" [disabled]="streaming() || !draft.trim()">
            <i class="ri-send-plane-2-fill"></i>
          </button>
        </form>
      </aside>
    }

    @if (orbVisible()) {
      <app-speak-orb
        [speaking]="orbSpeaking()"
        [excerpt]="orbExcerpt()"
        (stopped)="stopSpeak()"
      ></app-speak-orb>
    }
  `,
  styles: [
    `
      :host-context(html.dpu-kiosk-mode) {
        display: none !important;
      }
      .sv-ask-fab {
        position: fixed;
        right: 1.35rem;
        bottom: 1.35rem;
        z-index: 1050;
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.65rem 1.05rem;
        border-radius: 9999px;
        border: 1px solid rgba(20, 184, 166, 0.5);
        background: linear-gradient(135deg, #070d14, #0f172a);
        color: #e2e8f0;
        font-size: 0.85rem;
        font-weight: 700;
        box-shadow: 0 12px 32px rgba(2, 6, 23, 0.55), 0 0 20px rgba(20, 184, 166, 0.25);
        cursor: pointer;
        transition: transform 0.2s ease, border-color 0.2s ease;
      }
      .sv-ask-fab:hover {
        transform: translateY(-2px);
        border-color: #2dd4bf;
      }
      .sv-ask-dock {
        position: fixed;
        right: 1.25rem;
        bottom: 4.75rem;
        z-index: 1060;
        width: min(25rem, calc(100vw - 2rem));
        height: min(34rem, calc(100vh - 6.5rem));
        display: flex;
        flex-direction: column;
        border-radius: 1.15rem;
        border: 1px solid rgba(148, 163, 184, 0.22);
        background: rgba(7, 13, 20, 0.96);
        backdrop-filter: blur(16px);
        box-shadow: 0 24px 64px rgba(0, 0, 0, 0.65);
        overflow: hidden;
      }
      .sv-ask-dock__header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 1rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.14);
      }
      .sv-ask-dock__dot {
        width: 8px;
        height: 8px;
        border-radius: 9999px;
        background: #14b8a6;
        box-shadow: 0 0 10px #14b8a6;
      }
      .sv-ask-dock__close {
        background: transparent;
        border: 0;
        color: #94a3b8;
        font-size: 1.15rem;
        cursor: pointer;
      }
      .sv-ask-dock__chips {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        padding: 0.6rem 0.85rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.1);
      }
      .sv-ask-chip {
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        border: 1px solid rgba(56, 189, 248, 0.3);
        background: rgba(56, 189, 248, 0.1);
        color: #bae6fd;
        font-size: 0.72rem;
        cursor: pointer;
      }
      .sv-ask-dock__messages {
        flex: 1;
        overflow-y: auto;
        padding: 0.85rem;
        display: flex;
        flex-direction: column;
        gap: 0.7rem;
      }
      .sv-ask-msg {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 0.25rem;
      }
      .sv-ask-msg.is-user {
        align-items: flex-end;
      }
      .sv-ask-msg__bubble {
        max-width: 90%;
        padding: 0.55rem 0.8rem;
        border-radius: 0.85rem;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #e2e8f0;
        font-size: 0.82rem;
        line-height: 1.5;
        white-space: pre-wrap;
      }
      .sv-ask-msg.is-user .sv-ask-msg__bubble {
        background: rgba(20, 184, 166, 0.22);
        border-color: rgba(20, 184, 166, 0.4);
      }
      .sv-ask-speak-btn {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        background: transparent;
        border: 0;
        color: #38bdf8;
        font-size: 0.72rem;
        cursor: pointer;
      }
      .sv-ask-dock__form {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.65rem 0.75rem;
        border-top: 1px solid rgba(148, 163, 184, 0.14);
      }
      .sv-ask-input {
        flex: 1;
        min-width: 0;
        padding: 0.5rem 0.75rem;
        border-radius: 0.7rem;
        border: 1px solid rgba(148, 163, 184, 0.24);
        background: rgba(15, 23, 42, 0.8);
        color: #f1f5f9;
        font-size: 0.82rem;
      }
      .sv-ask-mic,
      .sv-ask-send {
        width: 34px;
        height: 34px;
        border-radius: 9999px;
        border: 1px solid rgba(148, 163, 184, 0.25);
        background: rgba(255, 255, 255, 0.06);
        color: #e2e8f0;
        display: grid;
        place-items: center;
        cursor: pointer;
      }
      .sv-ask-mic.is-listening {
        border-color: #f43f5e;
        background: rgba(244, 63, 94, 0.22);
        color: #fda4af;
      }
      .sv-ask-send {
        background: #0f766e;
        border-color: #14b8a6;
      }
    `,
  ],
})
export class AskDockComponent implements OnDestroy {
  private readonly tokenService = inject(TokenService);
  private readonly audioSfx = inject(AudioSfxService);
  private readonly sileroVad = inject(SileroVadService);

  readonly open = signal(false);
  readonly streaming = signal(false);
  readonly listening = signal(false);
  readonly statusLabel = signal('');
  readonly messages = signal<ChatTurn[]>([]);
  readonly orbVisible = signal(false);
  readonly orbSpeaking = signal(false);
  readonly orbExcerpt = signal('');

  draft = '';
  readonly quickPrompts = [
    'สรุปสถานะลงเวลาและเหตุการณ์วันนี้',
    'มี Incident ที่ยังเปิดอยู่ไหม?',
    'สถานะกล้องและ Access Zones',
  ];

  private abortCtrl: AbortController | null = null;
  private recognition: unknown = null;

  toggleOpen(): void {
    const next = !this.open();
    this.open.set(next);
    this.audioSfx.playTick();
  }

  submit(): void {
    const q = this.draft.trim();
    if (!q || this.streaming()) return;
    this.draft = '';
    void this.ask(q);
  }

  async ask(question: string): Promise<void> {
    const companyId = this.tokenService.getSelectCompany()?.companyId;
    if (!companyId) return;

    this.audioSfx.playBeep();
    const history = this.messages().slice(-6);
    this.messages.update((prev) => [...prev, { role: 'user', content: question }, { role: 'assistant', content: '' }]);
    this.streaming.set(true);
    this.statusLabel.set('กำลังเชื่อมต่อ Copilot...');

    this.abortCtrl?.abort();
    this.abortCtrl = new AbortController();

    try {
      const token = this.tokenService.getToken();
      const resp = await fetch(`/sentinel/company/${companyId}/assistant/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ question, history }),
        signal: this.abortCtrl.signal,
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = 'token';

      for (let chunk = await reader.read(); !chunk.done; chunk = await reader.read()) {
        const value = chunk.value;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const rawLine of lines) {
          const line = rawLine.trim();
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            const dataStr = line.slice(5).trim();
            if (!dataStr) continue;
            try {
              const payload = JSON.parse(dataStr) as { text?: string; label?: string };
              if (currentEvent === 'status' && payload.label) {
                this.statusLabel.set(payload.label);
              } else if (currentEvent === 'token' && payload.text) {
                this.messages.update((list) => {
                  const copy = [...list];
                  const last = copy[copy.length - 1];
                  if (last && last.role === 'assistant') {
                    copy[copy.length - 1] = { ...last, content: last.content + payload.text };
                  }
                  return copy;
                });
              }
            } catch {
              // ignore malformed SSE chunk
            }
          }
        }
      }
      this.audioSfx.playChime();
    } catch {
      this.messages.update((list) => {
        const copy = [...list];
        const last = copy[copy.length - 1];
        if (last && last.role === 'assistant' && !last.content) {
          copy[copy.length - 1] = {
            ...last,
            content: 'ไม่สามารถเชื่อมต่อ Copilot ได้ในขณะนี้ กรุณาลองใหม่อีกครั้ง',
          };
        }
        return copy;
      });
    } finally {
      this.streaming.set(false);
      this.statusLabel.set('');
    }
  }

  async toggleVoice(): Promise<void> {
    if (this.listening()) {
      (this.recognition as { stop?: () => void } | null)?.stop?.();
      this.listening.set(false);
      return;
    }
    void this.sileroVad.init();
    const w = window as unknown as {
      SpeechRecognition?: new () => Record<string, unknown>;
      webkitSpeechRecognition?: new () => Record<string, unknown>;
    };
    const SR = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!SR) {
      this.statusLabel.set('เบราว์เซอร์นี้ไม่รองรับ SpeechRecognition');
      return;
    }
    const rec = new SR();
    rec['lang'] = 'th-TH';
    rec['interimResults'] = false;
    rec['onresult'] = (ev: { results?: ArrayLike<ArrayLike<{ transcript?: string }>> }) => {
      const text = ev?.results?.[0]?.[0]?.transcript?.trim();
      if (text) {
        this.draft = text;
        this.submit();
      }
    };
    rec['onend'] = () => this.listening.set(false);
    rec['onerror'] = () => this.listening.set(false);
    this.recognition = rec;
    this.listening.set(true);
    this.audioSfx.playTick();
    (rec['start'] as () => void)();
  }

  speak(text: string): void {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = /[ก-ฮ]/.test(text) ? 'th-TH' : 'en-US';
    this.orbExcerpt.set(text.slice(0, 220));
    this.orbVisible.set(true);
    this.orbSpeaking.set(true);
    utter.onend = () => {
      this.orbSpeaking.set(false);
      this.orbVisible.set(false);
    };
    utter.onerror = () => {
      this.orbSpeaking.set(false);
      this.orbVisible.set(false);
    };
    window.speechSynthesis.speak(utter);
  }

  stopSpeak(): void {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    this.orbSpeaking.set(false);
    this.orbVisible.set(false);
  }

  ngOnDestroy(): void {
    this.abortCtrl?.abort();
    this.stopSpeak();
  }
}
