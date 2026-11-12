import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import { SmoothBox, lerpBox } from '../company-emp.helpers';

export type BrowserFaceDetector = {
  detect: (
    source: HTMLVideoElement,
  ) => Promise<Array<{ boundingBox: { x: number; y: number; width: number; height: number } }>>;
};

export type VideoInputDevice = {
  deviceId: string;
  label: string;
};

export async function listVideoInputDevices(): Promise<VideoInputDevice[]> {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices
    .filter((d) => d.kind === 'videoinput' && d.deviceId)
    .map((d, i) => ({
      deviceId: d.deviceId,
      label: (d.label || '').trim() || `Camera ${i + 1}`,
    }));
}

export async function openUserCamera(deviceId?: string | null): Promise<MediaStream> {
  try {
    const video: MediaTrackConstraints = {
      width: { ideal: 1280 },
      height: { ideal: 720 },
    };
    if (deviceId) {
      video.deviceId = { exact: deviceId };
    } else {
      video.facingMode = 'user';
    }
    return await navigator.mediaDevices.getUserMedia({ video });
  } catch (err) {
    console.error('Error accessing camera: ', err);
    // Exact deviceId can fail if the device disappeared — retry with default.
    if (deviceId) {
      try {
        return await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        });
      } catch {
        /* fall through */
      }
    }
    throw new Error('ไม่สามารถเปิดกล้องได้ กรุณาอนุญาตการใช้กล้องในเบราว์เซอร์');
  }
}

export function stopMediaStream(stream: MediaStream | null, videoEl?: HTMLVideoElement | null): void {
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
  }
  if (videoEl) {
    videoEl.srcObject = null;
  }
}

export function createBrowserFaceDetector(): BrowserFaceDetector | null {
  const FaceDetectorCtor = (
    globalThis as { FaceDetector?: new (opts?: object) => BrowserFaceDetector }
  ).FaceDetector;
  if (typeof FaceDetectorCtor !== 'function') return null;
  try {
    return new FaceDetectorCtor({ fastMode: true, maxDetectedFaces: 1 });
  } catch {
    return null;
  }
}

/**
 * Map a box in video-frame pixels onto the overlay element, matching
 * CSS ``object-fit: contain`` (letterbox). Using plain client/frame ratios
 * breaks on phones (portrait stream in a wide card) and the box disappears.
 */
export function mapFrameBoxToElement(
  box: { x: number; y: number; width: number; height: number },
  frameW: number,
  frameH: number,
  elementW: number,
  elementH: number,
  fit: 'contain' | 'cover' = 'contain',
): SmoothBox {
  const fw = Math.max(1, frameW);
  const fh = Math.max(1, frameH);
  const ew = Math.max(1, elementW);
  const eh = Math.max(1, elementH);
  const scale =
    fit === 'cover' ? Math.max(ew / fw, eh / fh) : Math.min(ew / fw, eh / fh);
  const dispW = fw * scale;
  const dispH = fh * scale;
  const ox = (ew - dispW) / 2;
  const oy = (eh - dispH) / 2;
  return {
    x: box.x * scale + ox,
    y: box.y * scale + oy,
    width: box.width * scale,
    height: box.height * scale,
  };
}

export async function detectBrowserFaceBox(
  faceDetector: BrowserFaceDetector | null,
  videoEl: HTMLVideoElement,
  liveSize: { width: number; height: number },
): Promise<SmoothBox | null> {
  if (!faceDetector) return null;
  try {
    const faces = await faceDetector.detect(videoEl);
    const box = faces[0]?.boundingBox;
    if (!box || box.width < 8 || box.height < 8) return null;
    return mapFrameBoxToElement(
      box,
      videoEl.videoWidth || liveSize.width,
      videoEl.videoHeight || liveSize.height,
      liveSize.width,
      liveSize.height,
      'contain',
    );
  } catch {
    // Some mobile WebViews throw from FaceDetector on certain frames.
    return null;
  }
}

export type ServerEnrollDetectResult = {
  box: SmoothBox | null;
  enrollReady: boolean;
  enrollMessage: string;
  faceRatio?: number | null;
  minFaceRatio?: number | null;
};

export async function detectServerFaceBox(
  http: HttpClient,
  videoEl: HTMLVideoElement,
  liveSize: { width: number; height: number },
  enrollDetectCanvas: HTMLCanvasElement,
  forEnrollment = false,
): Promise<ServerEnrollDetectResult> {
  const empty: ServerEnrollDetectResult = {
    box: null,
    enrollReady: false,
    enrollMessage: 'No face detected',
  };
  const vw = videoEl.videoWidth || 640;
  const vh = videoEl.videoHeight || 480;
  const targetW = 480;
  const scale = Math.min(1, targetW / vw);
  const w = Math.max(1, Math.round(vw * scale));
  const h = Math.max(1, Math.round(vh * scale));
  if (enrollDetectCanvas.width !== w || enrollDetectCanvas.height !== h) {
    enrollDetectCanvas.width = w;
    enrollDetectCanvas.height = h;
  }
  const ctx = enrollDetectCanvas.getContext('2d');
  if (!ctx) return empty;
  ctx.drawImage(videoEl, 0, 0, w, h);
  const blob = await new Promise<Blob | null>((resolve) =>
    enrollDetectCanvas.toBlob((b) => resolve(b), 'image/jpeg', 0.7),
  );
  if (!blob) return empty;
  const form = new FormData();
  form.append('file', blob, 'enroll-detect.jpg');
  if (forEnrollment) {
    form.append('forEnrollment', 'true');
  }
  const res = await firstValueFrom(
    http.post<{
      faces?: Array<{ x: number; y: number; width: number; height: number; score?: number }>;
      frameWidth?: number;
      frameHeight?: number;
      enrollReady?: boolean;
      enrollMessage?: string;
      enrollScores?: { faceRatio?: number };
      minFaceRatio?: number;
    }>(environment.baseUrl + '/face/detect', form),
  );
  const faces = res?.faces || [];
  const face =
    faces.length <= 1
      ? faces[0]
      : faces.reduce((a, b) =>
          a.width * a.height >= b.width * b.height ? a : b,
        );
  if (!face || face.width < 8 || face.height < 8) {
    return {
      ...empty,
      enrollMessage: res?.enrollMessage || 'No face detected',
      minFaceRatio: res?.minFaceRatio ?? null,
    };
  }
  const fw = res.frameWidth || w;
  const fh = res.frameHeight || h;
  // Server boxes are in the downscaled JPEG we uploaded; map that space →
  // full video frame first, then onto the on-screen element (object-fit contain).
  const frameScaleX = vw / fw;
  const frameScaleY = vh / fh;
  const inVideo = {
    x: face.x * frameScaleX,
    y: face.y * frameScaleY,
    width: face.width * frameScaleX,
    height: face.height * frameScaleY,
  };
  return {
    box: mapFrameBoxToElement(inVideo, vw, vh, liveSize.width, liveSize.height, 'contain'),
    enrollReady: forEnrollment ? !!res?.enrollReady : true,
    enrollMessage: res?.enrollMessage || (res?.enrollReady ? 'ok' : 'Face not ready'),
    faceRatio: res?.enrollScores?.faceRatio ?? null,
    minFaceRatio: res?.minFaceRatio ?? null,
  };
}

export function smoothFaceBox(
  prev: SmoothBox | null,
  next: SmoothBox,
  t: number,
): SmoothBox {
  return lerpBox(prev, next, t);
}

export function drawSmoothOverlay(
  ctx: CanvasRenderingContext2D,
  box: SmoothBox,
  label: string | null,
  ready: boolean,
  busy: boolean,
): void {
  const pad = 6;
  const x = box.x - pad;
  const y = box.y - pad;
  const w = box.width + pad * 2;
  const h = box.height + pad * 2;
  const radius = 14;

  let stroke = 'rgba(148, 163, 184, 0.9)';
  let corner = '#94a3b8';
  let labelBg = 'rgba(51, 65, 85, 0.92)';
  if (ready && !busy) {
    stroke = 'rgba(52, 211, 153, 0.95)';
    corner = '#34d399';
    labelBg = 'rgba(6, 95, 70, 0.92)';
  } else if (busy) {
    stroke = 'rgba(251, 191, 36, 0.95)';
    corner = '#fbbf24';
    labelBg = 'rgba(146, 64, 14, 0.92)';
  } else if (label) {
    stroke = 'rgba(45, 212, 191, 0.95)';
    corner = '#5eead4';
    labelBg = 'rgba(15, 118, 110, 0.92)';
  }

  ctx.save();
  ctx.lineWidth = 3;
  ctx.strokeStyle = stroke;
  ctx.shadowColor = stroke;
  ctx.shadowBlur = 8;
  roundRect(ctx, x, y, w, h, radius);
  ctx.stroke();
  ctx.shadowBlur = 0;

  const c = Math.min(28, w * 0.22, h * 0.22);
  ctx.lineWidth = 4;
  ctx.strokeStyle = corner;
  ctx.beginPath();
  ctx.moveTo(x, y + c);
  ctx.lineTo(x, y);
  ctx.lineTo(x + c, y);
  ctx.moveTo(x + w - c, y);
  ctx.lineTo(x + w, y);
  ctx.lineTo(x + w, y + c);
  ctx.moveTo(x + w, y + h - c);
  ctx.lineTo(x + w, y + h);
  ctx.lineTo(x + w - c, y + h);
  ctx.moveTo(x + c, y + h);
  ctx.lineTo(x, y + h);
  ctx.lineTo(x, y + h - c);
  ctx.stroke();

  if (label) {
    ctx.font = '600 15px "Segoe UI", system-ui, sans-serif';
    const metrics = ctx.measureText(label);
    const labelPadX = 10;
    const labelH = 26;
    const labelW = metrics.width + labelPadX * 2;
    const labelX = x;
    const labelY = Math.max(8, y - labelH - 6);
    ctx.fillStyle = labelBg;
    roundRect(ctx, labelX, labelY, labelW, labelH, 8);
    ctx.fill();
    ctx.fillStyle = '#ecfdf5';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, labelX + labelPadX, labelY + labelH / 2 + 1);
  }
  ctx.restore();
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
): void {
  const radius = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + w, y, x + w, y + h, radius);
  ctx.arcTo(x + w, y + h, x, y + h, radius);
  ctx.arcTo(x, y + h, x, y, radius);
  ctx.arcTo(x, y, x + w, y, radius);
  ctx.closePath();
}
