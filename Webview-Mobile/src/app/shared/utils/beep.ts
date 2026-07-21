/** Short UI beeps via Web Audio API (no asset files). */

let sharedCtx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  try {
    const AC = window.AudioContext || (window as any).webkitAudioContext;
    if (!AC) {
      return null;
    }
    if (!sharedCtx) {
      sharedCtx = new AC();
    }
    return sharedCtx;
  } catch {
    return null;
  }
}

export function unlockBeepAudio(): void {
  const ctx = getCtx();
  if (ctx?.state === 'suspended') {
    void ctx.resume();
  }
}

function tone(
  frequency: number,
  durationMs: number,
  when = 0,
  volume = 0.12,
  type: OscillatorType = 'sine',
): void {
  const ctx = getCtx();
  if (!ctx) {
    return;
  }
  if (ctx.state === 'suspended') {
    void ctx.resume();
  }
  const t0 = ctx.currentTime + when;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.value = frequency;
  gain.gain.setValueAtTime(0.0001, t0);
  gain.gain.exponentialRampToValueAtTime(volume, t0 + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + durationMs / 1000);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(t0);
  osc.stop(t0 + durationMs / 1000 + 0.02);
}

export function playCaptureBeep(): void {
  tone(1046, 90, 0, 0.14);
}

export function playCheckInBeep(): void {
  tone(880, 80, 0, 0.13);
  tone(1319, 110, 0.1, 0.14);
}
