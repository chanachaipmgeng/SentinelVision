/** Capture interval policy when the GPU queue is backed up. */
export const KIOSK_CAPTURE_INTERVAL_MS = 400;

/** Idle screens with no faces — still ping detect, but slower. */
export const KIOSK_IDLE_CAPTURE_INTERVAL_MS = 400;

export function nextCaptureInterval(
  queueDepth: number,
  opts?: { idleNoFaces?: boolean },
): number {
  let ms = 90;
  if (queueDepth >= 32) {
    ms = 800;
  } else if (queueDepth >= 8) {
    ms = 500;
  }
  if (opts?.idleNoFaces) {
    return Math.max(KIOSK_IDLE_CAPTURE_INTERVAL_MS, ms);
  }
  return ms;
}
