import { SmoothBox } from '../overlay/kiosk-box';

export const DETECT_THUMB_W = 32;
export const DETECT_THUMB_H = 24;
export const DETECT_FRAME_TARGET_W = 480;

export type UserMediaResult =
  | { ok: true; stream: MediaStream }
  | { ok: false; error: unknown };

/** Start the facing-user camera stream (caller owns stop()). */
export async function startUserMedia(
  constraints: MediaStreamConstraints = { video: { facingMode: 'user' } },
): Promise<UserMediaResult> {
  try {
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    return { ok: true, stream };
  } catch (error) {
    return { ok: false, error };
  }
}

/** Ensure a canvas exists at the requested size (reuses `existing` when possible). */
export function ensureCanvas(
  existing: HTMLCanvasElement | null,
  width: number,
  height: number,
): HTMLCanvasElement {
  const canvas = existing ?? document.createElement('canvas');
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  return canvas;
}

/**
 * Downscale a live video frame onto a detect canvas for WS `detect`.
 * Returns null when the 2d context is unavailable.
 */
export function prepareDetectFrame(
  videoEl: HTMLVideoElement,
  existingCanvas: HTMLCanvasElement | null,
  targetW = DETECT_FRAME_TARGET_W,
): { canvas: HTMLCanvasElement; width: number; height: number } | null {
  const vw = videoEl.videoWidth || 640;
  const vh = videoEl.videoHeight || 480;
  const scale = Math.min(1, targetW / vw);
  const w = Math.round(vw * scale);
  const h = Math.round(vh * scale);
  const canvas = ensureCanvas(existingCanvas, w, h);
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) {
    return null;
  }
  ctx.drawImage(videoEl, 0, 0, w, h);
  return { canvas, width: w, height: h };
}

/** 32×24 RGBA sample used for motion gating (cheap vs JPEG). */
export function sampleDetectThumb(
  source: HTMLCanvasElement,
  existingThumb: HTMLCanvasElement | null,
): { pixels: Uint8ClampedArray; canvas: HTMLCanvasElement } {
  const thumb = ensureCanvas(existingThumb, DETECT_THUMB_W, DETECT_THUMB_H);
  const tctx = thumb.getContext('2d', { willReadFrequently: true });
  if (!tctx) {
    return {
      pixels: new Uint8ClampedArray(DETECT_THUMB_W * DETECT_THUMB_H * 4),
      canvas: thumb,
    };
  }
  tctx.drawImage(source, 0, 0, DETECT_THUMB_W, DETECT_THUMB_H);
  return {
    pixels: new Uint8ClampedArray(tctx.getImageData(0, 0, DETECT_THUMB_W, DETECT_THUMB_H).data),
    canvas: thumb,
  };
}

export type FaceCropOpts = {
  cropPad?: number;
  /** Display (canvas) size of the video element. */
  displayWidth: number;
  displayHeight: number;
  /** Intrinsic video frame size. */
  videoWidth: number;
  videoHeight: number;
};

/**
 * Map a display-space box to video pixels, pad, and JPEG-encode a square crop.
 * Pure aside from reading pixels from `video` / creating a canvas.
 */
export function captureFaceCrop(
  video: CanvasImageSource,
  box: SmoothBox,
  opts: FaceCropOpts,
): string | null {
  const cropPad = opts.cropPad ?? 0.4;
  const vw = opts.videoWidth || 640;
  const vh = opts.videoHeight || 480;
  const dw = opts.displayWidth || 640;
  const dh = opts.displayHeight || 480;

  const padX = box.width * cropPad;
  const padY = box.height * cropPad;
  let x = ((box.x - padX) / dw) * vw;
  let y = ((box.y - padY) / dh) * vh;
  let w = ((box.width + padX * 2) / dw) * vw;
  let h = ((box.height + padY * 2) / dh) * vh;

  x = Math.max(0, Math.min(x, vw - 2));
  y = Math.max(0, Math.min(y, vh - 2));
  w = Math.max(32, Math.min(w, vw - x));
  h = Math.max(32, Math.min(h, vh - y));

  const out = Math.max(160, Math.min(320, Math.round(Math.max(w, h))));
  const canvas = document.createElement('canvas');
  canvas.width = out;
  canvas.height = out;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    return null;
  }
  ctx.drawImage(video, x, y, w, h, 0, 0, out, out);
  return canvas.toDataURL('image/jpeg', 0.88);
}

/** Scale server detect boxes from frame space into display coordinates. */
export function scaleDetectionBoxes(
  faces: Array<{ x?: unknown; y?: unknown; width?: unknown; height?: unknown }>,
  frameW: number,
  frameH: number,
  displayW: number,
  displayH: number,
): SmoothBox[] {
  const sx = displayW / (frameW || 1);
  const sy = displayH / (frameH || 1);
  return faces.map((f) => ({
    x: Number(f.x) * sx,
    y: Number(f.y) * sy,
    width: Number(f.width) * sx,
    height: Number(f.height) * sy,
  }));
}

/** Convert a data-URL to a File for HTTP FormData fallback. */
export function dataURLtoFile(dataurl: string, filename: string): File {
  const arr = dataurl.split(',');
  const mimeMatch = arr[0].match(/:(.*?);/);
  const mime = mimeMatch ? mimeMatch[1] : 'application/octet-stream';
  const bstr = atob(arr[1] ?? '');
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }
  return new File([u8arr], filename, { type: mime });
}
