/** Capture interval policy when the GPU queue is backed up. */
export const KIOSK_CAPTURE_INTERVAL_MS = 400;

export function nextCaptureInterval(queueDepth: number): number {
  if (queueDepth >= 32) {
    return 800;
  }
  if (queueDepth >= 8) {
    return 500;
  }
  return KIOSK_CAPTURE_INTERVAL_MS;
}
