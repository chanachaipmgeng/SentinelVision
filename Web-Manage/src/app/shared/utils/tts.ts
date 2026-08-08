/** Browser SpeechSynthesis helper (v1). Swap for CloudTtsSpeaker later. */

export interface TtsSpeakOptions {
  lang?: string;
  rate?: number;
  pitch?: number;
  /** When true (default), cancel any in-flight utterance first. */
  cancelPrevious?: boolean;
}

export interface TtsSpeaker {
  speak(text: string, opts?: TtsSpeakOptions): void;
  unlock(): void;
  cancel(): void;
}

let thaiVoice: SpeechSynthesisVoice | null = null;
let voicesLoaded = false;

function pickThaiVoice(): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    return null;
  }
  const voices = window.speechSynthesis.getVoices() || [];
  if (!voices.length) {
    return thaiVoice;
  }
  const th =
    voices.find((v) => /^th(-|$)/i.test(v.lang)) ||
    voices.find((v) => /thai/i.test(v.name)) ||
    null;
  thaiVoice = th;
  voicesLoaded = true;
  return th;
}

function ensureVoices(): void {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    return;
  }
  pickThaiVoice();
  if (!voicesLoaded) {
    window.speechSynthesis.onvoiceschanged = () => {
      pickThaiVoice();
    };
  }
}

export class BrowserTtsSpeaker implements TtsSpeaker {
  unlock(): void {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      return;
    }
    ensureVoices();
    // Some browsers need a no-op speak after a user gesture.
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance('');
      u.volume = 0;
      window.speechSynthesis.speak(u);
      window.speechSynthesis.cancel();
    } catch {
      /* ignore */
    }
  }

  cancel(): void {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      return;
    }
    try {
      window.speechSynthesis.cancel();
    } catch {
      /* ignore */
    }
  }

  speak(text: string, opts: TtsSpeakOptions = {}): void {
    const trimmed = (text || '').trim();
    if (!trimmed || typeof window === 'undefined' || !window.speechSynthesis) {
      return;
    }
    ensureVoices();
    if (opts.cancelPrevious !== false) {
      this.cancel();
    }
    const u = new SpeechSynthesisUtterance(trimmed);
    u.lang = opts.lang || 'th-TH';
    u.rate = typeof opts.rate === 'number' ? opts.rate : 1;
    u.pitch = typeof opts.pitch === 'number' ? opts.pitch : 1;
    const voice = pickThaiVoice();
    if (voice) {
      u.voice = voice;
    }
    try {
      window.speechSynthesis.speak(u);
    } catch {
      /* ignore */
    }
  }
}

const defaultSpeaker: TtsSpeaker = new BrowserTtsSpeaker();

export function unlockSpeech(): void {
  defaultSpeaker.unlock();
}

export function cancelSpeech(): void {
  defaultSpeaker.cancel();
}

export function speakText(text: string, opts?: TtsSpeakOptions): void {
  defaultSpeaker.speak(text, opts);
}

export function getTtsSpeaker(): TtsSpeaker {
  return defaultSpeaker;
}
