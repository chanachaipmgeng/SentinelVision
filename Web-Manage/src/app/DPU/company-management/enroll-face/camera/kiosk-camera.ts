import { SmoothBox } from '../overlay/kiosk-box';

export const DETECT_THUMB_W = 32;
export const DETECT_THUMB_H = 24;
export const DETECT_FRAME_TARGET_W = 480;

export type UserMediaResult =
  | { ok: true; stream: MediaStream }
  | { ok: false; error: unknown };

/** Why getUserMedia failed — drives recovery copy on the kiosk. */
export type CameraFailureKind =
  | 'permission'
  | 'not_found'
  | 'in_use'
  | 'insecure'
  | 'unsupported'
  | 'unknown';

export type CameraRecoveryInfo = {
  kind: CameraFailureKind;
  /** Short Thai title shown in the recovery panel / status. */
  title: string;
  /** Numbered operator steps (Thai, with familiar EN UI terms). */
  steps: string[];
};

function cameraErrorName(error: unknown): string {
  if (error && typeof error === 'object' && 'name' in error) {
    return String((error as { name?: unknown }).name || '');
  }
  return '';
}

/**
 * Map a getUserMedia failure into actionable recovery copy.
 * Pure — safe to unit-test without a real camera.
 */
export function describeCameraFailure(error: unknown): CameraRecoveryInfo {
  const name = cameraErrorName(error);
  const message =
    error && typeof error === 'object' && 'message' in error
      ? String((error as { message?: unknown }).message || '')
      : typeof error === 'string'
        ? error
        : '';

  if (
    name === 'NotAllowedError' ||
    name === 'PermissionDeniedError' ||
    /permission|denied|notallowed/i.test(`${name} ${message}`)
  ) {
    return {
      kind: 'permission',
      title: 'ไม่สามารถเปิดกล้องได้ — ถูกปฏิเสธสิทธิ์ (Permission denied)',
      steps: [
        'คลิกไอคอนกล้อง / แม่กุญแจในแถบที่อยู่ของเบราว์เซอร์ (address bar)',
        'ตั้ง Camera เป็น Allow / อนุญาต แล้วกด Retry ด้านล่าง',
        'ถ้าเคยกด Block: เปิด Site settings → Camera → Allow แล้วรีเฟรชหน้า',
        'บนแท็บเล็ต/มือถือ: ตรวจ Settings ของระบบว่าแอปเบราว์เซอร์ใช้กล้องได้',
      ],
    };
  }

  if (name === 'NotFoundError' || name === 'DevicesNotFoundError' || /notfound|no device/i.test(message)) {
    return {
      kind: 'not_found',
      title: 'ไม่พบกล้อง (No camera device)',
      steps: [
        'ตรวจว่ากล้องเสียบอยู่ / ไม่ถูกปิดด้วยฮาร์ดแวร์สวิตช์',
        'ปิดแอปอื่นที่อาจจองกล้อง แล้วกด Retry',
        'ในเบราว์เซอร์: Site settings → Camera ต้องไม่ถูกบล็อก',
        'เครื่อง headless / VM ที่ไม่มีกล้อง: ใช้ Admin preview เพื่อตรวจ chrome',
      ],
    };
  }

  if (name === 'NotReadableError' || name === 'TrackStartError' || /in use|busy|readable/i.test(message)) {
    return {
      kind: 'in_use',
      title: 'กล้องถูกใช้อยู่ (Camera in use)',
      steps: [
        'ปิดโปรแกรมประชุม / แอปกล้องอื่นที่เปิดค้าง',
        'ถอดและเสียบกล้องใหม่ถ้าเป็น USB cam',
        'กด Retry เพื่อขอ media อีกครั้ง',
      ],
    };
  }

  if (
    name === 'NotSupportedError' ||
    typeof navigator === 'undefined' ||
    !navigator.mediaDevices ||
    typeof navigator.mediaDevices.getUserMedia !== 'function'
  ) {
    return {
      kind: 'unsupported',
      title: 'เบราว์เซอร์นี้ไม่รองรับกล้อง (getUserMedia)',
      steps: [
        'ใช้ Chrome / Edge / Safari รุ่นล่าสุดบนอุปกรณ์ kiosk',
        'ตรวจว่าไม่ได้เปิดโหมดที่ปิด media devices',
        'ใช้ Admin preview เพื่อตรวจ UI chrome ชั่วคราว',
      ],
    };
  }

  const host =
    typeof window !== 'undefined' && window.location ? window.location.hostname : '';
  const insecure =
    typeof window !== 'undefined' &&
    !window.isSecureContext &&
    host !== 'localhost' &&
    host !== '127.0.0.1';
  if (name === 'SecurityError' || insecure) {
    return {
      kind: 'insecure',
      title: 'ต้องเปิดผ่าน HTTPS ถึงใช้กล้องได้ (Secure context)',
      steps: [
        'เปิด kiosk ด้วย https:// หรือ http://localhost',
        'อย่าใช้ IP แบบ HTTP บน LAN (เบราว์เซอร์จะบล็อก getUserMedia)',
        'หลังเปลี่ยน URL แล้วกด Retry',
      ],
    };
  }

  return {
    kind: 'unknown',
    title: 'ไม่สามารถเปิดกล้องได้',
    steps: [
      'อนุญาต Camera ในเบราว์เซอร์ แล้วกด Retry',
      'ตรวจว่ามีกล้องและไม่ถูกแอปอื่นจอง',
      'ถ้ายังไม่ได้: ใช้ Admin preview เพื่อตรวจ chrome โดยไม่ใช้กล้อง',
    ],
  };
}

/** Start the facing-user camera stream (caller owns stop()). */
export async function startUserMedia(
  constraints: MediaStreamConstraints = { video: { facingMode: 'user' } },
): Promise<UserMediaResult> {
  try {
    if (!navigator.mediaDevices?.getUserMedia) {
      return { ok: false, error: { name: 'NotSupportedError', message: 'getUserMedia unavailable' } };
    }
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
