import { Injectable, signal } from '@angular/core';
import { FilesetResolver, GestureRecognizer } from '@mediapipe/tasks-vision';

export type KioskGestureAction = 'confirm' | 'toggle_scan' | 'toggle_large_text' | 'mute_audio';

export interface KioskGestureEvent {
  rawGesture: string;
  action: KioskGestureAction;
  label: string;
  confidence: number;
  ts: number;
}

const GESTURE_TO_ACTION: Record<string, { action: KioskGestureAction; label: string }> = {
  Thumb_Up: { action: 'confirm', label: '👍 Confirm / Capture' },
  Open_Palm: { action: 'toggle_scan', label: '✋ Pause / Resume' },
  Victory: { action: 'toggle_large_text', label: '✌️ Large Text' },
  Closed_Fist: { action: 'mute_audio', label: '✊ Mute / Unmute' },
};

/**
 * Touchless MediaPipe GestureRecognizer for SentinelVision Kiosk.
 * Opt-in, throttled to ~4 Hz, and requires consecutive hold frames before firing.
 */
@Injectable({ providedIn: 'root' })
export class KioskGestureService {
  private recognizer: GestureRecognizer | null = null;
  private initPromise: Promise<void> | null = null;
  private lastSampleAt = 0;
  private lastActionAt = 0;
  private heldGesture = '';
  private heldCount = 0;

  readonly ready = signal(false);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly activeGesture = signal<string | null>(null);
  readonly lastTriggered = signal<KioskGestureEvent | null>(null);

  async init(): Promise<void> {
    if (this.recognizer) {
      this.ready.set(true);
      return;
    }
    if (this.initPromise) {
      return this.initPromise;
    }
    this.loading.set(true);
    this.error.set(null);
    this.initPromise = (async () => {
      try {
        const vision = await FilesetResolver.forVisionTasks('/mediapipe');
        this.recognizer = await GestureRecognizer.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: '/models/gesture_recognizer.task',
            delegate: 'GPU',
          },
          runningMode: 'VIDEO',
          numHands: 1,
        });
        this.ready.set(true);
      } catch (err) {
        this.error.set(err instanceof Error ? err.message : 'Gesture model failed to load');
        this.ready.set(false);
      } finally {
        this.loading.set(false);
        this.initPromise = null;
      }
    })();
    return this.initPromise;
  }

  /** Sample a video frame (throttled to 250ms). Returns an action if held long enough. */
  processFrame(video: HTMLVideoElement, nowMs = performance.now()): KioskGestureEvent | null {
    if (!this.recognizer || video.readyState < 2) {
      return null;
    }
    if (nowMs - this.lastSampleAt < 250) {
      return null;
    }
    this.lastSampleAt = nowMs;

    const result = this.recognizer.recognizeForVideo(video, nowMs);
    const top = result.gestures?.[0]?.[0];
    if (!top || top.score < 0.62 || top.categoryName === 'None') {
      this.heldGesture = '';
      this.heldCount = 0;
      this.activeGesture.set(null);
      return null;
    }

    const name = top.categoryName;
    const mapped = GESTURE_TO_ACTION[name];
    if (!mapped) {
      this.heldGesture = '';
      this.heldCount = 0;
      this.activeGesture.set(null);
      return null;
    }

    this.activeGesture.set(mapped.label);
    if (this.heldGesture === name) {
      this.heldCount += 1;
    } else {
      this.heldGesture = name;
      this.heldCount = 1;
    }

    // Require 2 consecutive samples (~500ms hold) and 2.2s cooldown
    if (this.heldCount >= 2 && nowMs - this.lastActionAt >= 2200) {
      this.lastActionAt = nowMs;
      this.heldCount = 0;
      const evt: KioskGestureEvent = {
        rawGesture: name,
        action: mapped.action,
        label: mapped.label,
        confidence: top.score,
        ts: Date.now(),
      };
      this.lastTriggered.set(evt);
      return evt;
    }

    return null;
  }

  dispose(): void {
    if (this.recognizer) {
      this.recognizer.close();
      this.recognizer = null;
    }
    this.ready.set(false);
    this.activeGesture.set(null);
    this.heldGesture = '';
    this.heldCount = 0;
  }
}
