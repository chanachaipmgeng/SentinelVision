/** Short UI beeps via Web Audio API (no asset files). */

let sharedCtx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  try {
    const AC =
      window.AudioContext ||
      (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
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

/** Call after a user gesture (open camera / click) so browsers allow audio. */
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

/** Single short beep — face angle captured. */
export function playCaptureBeep(): void {
  tone(1046, 90, 0, 0.14);
}

/** Double rising beep — check-in success. */
export function playCheckInBeep(): void {
  tone(880, 80, 0, 0.13);
  tone(1319, 110, 0.1, 0.14);
}

/** Bright triad — face identified / greeting on login. */
export function playFaceFoundBeep(): void {
  tone(784, 70, 0, 0.12);
  tone(988, 80, 0.08, 0.13);
  tone(1319, 120, 0.18, 0.15);
}

/** Soft lower beep — duplicate / already checked in. */
export function playDuplicateBeep(): void {
  tone(660, 70, 0, 0.1);
  tone(660, 70, 0.12, 0.08);
}

/** Soft warning beep — outside area. */
export function playWarningBeep(): void {
  tone(523, 100, 0, 0.12);
  tone(392, 140, 0.12, 0.12);
}

/** Incident sound registry: eventType → short Web Audio pattern. */
export type IncidentSoundKind = 'critical' | 'warning' | 'info' | 'access' | 'event';

const INCIDENT_SOUND_BY_EVENT: Record<string, IncidentSoundKind> = {
  BLACKLIST_ALERT: 'critical',
  ACCESS_DENIED: 'warning',
  ACCESS_GRANTED: 'access',
  VIP_ARRIVAL: 'info',
  VISITOR_CHECKIN: 'info',
  EVENT_CHECKIN: 'event',
};

const SOUND_PREF_KEY = 'dpu.incidentSoundEnabled';

/** User preference for new-incident toast audio (default on). */
export function isIncidentSoundEnabled(): boolean {
  try {
    const raw = localStorage.getItem(SOUND_PREF_KEY);
    if (raw === null) return true;
    return raw === '1' || raw === 'true';
  } catch {
    return true;
  }
}

export function setIncidentSoundEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(SOUND_PREF_KEY, enabled ? '1' : '0');
  } catch {
    /* ignore quota / private mode */
  }
}

function playIncidentKind(kind: IncidentSoundKind): void {
  switch (kind) {
    case 'critical':
      tone(880, 120, 0, 0.16, 'square');
      tone(660, 160, 0.14, 0.14, 'square');
      tone(520, 200, 0.3, 0.12, 'square');
      break;
    case 'warning':
      tone(740, 110, 0, 0.14);
      tone(620, 140, 0.13, 0.12);
      break;
    case 'access':
      tone(523, 70, 0, 0.1);
      break;
    case 'event':
      tone(784, 80, 0, 0.11);
      tone(988, 100, 0.1, 0.12);
      break;
    case 'info':
    default:
      tone(698, 90, 0, 0.11);
      break;
  }
}

/** Play the registered sound for an incident eventType (no-op if disabled). */
export function playIncidentEventSound(eventType?: string | null): void {
  if (!isIncidentSoundEnabled()) return;
  const key = String(eventType || '').trim().toUpperCase();
  playIncidentKind(INCIDENT_SOUND_BY_EVENT[key] || 'info');
}
