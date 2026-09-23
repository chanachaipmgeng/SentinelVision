/** Capture interval policy when the GPU queue is backed up. */
export const KIOSK_CAPTURE_INTERVAL_MS = 400;

/** Idle screens with no faces — still ping detect, but slower. */
export const KIOSK_IDLE_CAPTURE_INTERVAL_MS = 400;

/** Mean abs grayscale diff (0–255) below this = static scene. */
export const KIOSK_STATIC_SCENE_DIFF = 6;

/** Keep-alive when faces are tracked but the scene is still. */
export const KIOSK_STATIC_WITH_FACES_MS = 800;

/** Keep-alive when the scene is empty and still. */
export const KIOSK_STATIC_EMPTY_MS = 2000;

/** Locked tracks (identified / in check-in) — slower detect is fine. */
export const KIOSK_TRACKING_LOCKED_MS = 220;

/** All tracks done/cooldown — ping lightly. */
export const KIOSK_ALL_SETTLED_MS = 300;

export type CaptureIntervalOpts = {
  idleNoFaces?: boolean;
  /** Scene has barely changed vs previous thumbnail. */
  staticScene?: boolean;
  /** Every live track has memberId or is capturing/checking_in. */
  trackingLocked?: boolean;
  /** Every track is done or cooldown. */
  allSettled?: boolean;
  /** True when there is at least one active track. */
  hasTracks?: boolean;
};

/**
 * Mean absolute difference of grayscale-ish samples from two thumbnails.
 * Expects RGBA (or RGB) ImageData buffers of the same length.
 */
export function frameChangeScore(
  prev: Uint8ClampedArray | null,
  cur: Uint8ClampedArray,
): number {
  if (!prev || prev.length !== cur.length || cur.length < 4) {
    return 255;
  }
  let sum = 0;
  let n = 0;
  // Sample every pixel; use luminance from R/G/B (skip alpha).
  for (let i = 0; i < cur.length; i += 4) {
    const y0 = 0.299 * prev[i] + 0.587 * prev[i + 1] + 0.114 * prev[i + 2];
    const y1 = 0.299 * cur[i] + 0.587 * cur[i + 1] + 0.114 * cur[i + 2];
    sum += Math.abs(y1 - y0);
    n += 1;
  }
  return n > 0 ? sum / n : 255;
}

export function nextCaptureInterval(
  queueDepth: number,
  opts?: CaptureIntervalOpts,
): number {
  // Backpressure floor from queue depth.
  let ms = 90;
  if (queueDepth >= 32) {
    ms = 800;
  } else if (queueDepth >= 8) {
    ms = 500;
  }

  const idleNoFaces = !!opts?.idleNoFaces;
  const staticScene = !!opts?.staticScene;
  const hasTracks = !!opts?.hasTracks;
  const trackingLocked = !!opts?.trackingLocked;
  const allSettled = !!opts?.allSettled;

  if (staticScene && !hasTracks) {
    ms = Math.max(ms, KIOSK_STATIC_EMPTY_MS);
  } else if (staticScene && hasTracks) {
    ms = Math.max(ms, KIOSK_STATIC_WITH_FACES_MS);
  } else if (allSettled && hasTracks) {
    ms = Math.max(ms, KIOSK_ALL_SETTLED_MS);
  } else if (trackingLocked && hasTracks) {
    ms = Math.max(ms, KIOSK_TRACKING_LOCKED_MS);
  }

  if (idleNoFaces) {
    return Math.max(KIOSK_IDLE_CAPTURE_INTERVAL_MS, ms);
  }
  return ms;
}
