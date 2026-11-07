import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import { SmoothBox, lerpBox } from '../company-emp.helpers';

export type BrowserFaceDetector = {
  detect: (
    source: HTMLVideoElement,
  ) => Promise<Array<{ boundingBox: { x: number; y: number; width: number; height: number } }>>;
};

export async function openUserCamera(): Promise<MediaStream> {
  try {
    return await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
    });
  } catch (err) {
    console.error('Error accessing camera: ', err);
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

export async function detectBrowserFaceBox(
  faceDetector: BrowserFaceDetector | null,
  videoEl: HTMLVideoElement,
  liveSize: { width: number; height: number },
): Promise<SmoothBox | null> {
  if (!faceDetector) return null;
  const faces = await faceDetector.detect(videoEl);
  const box = faces[0]?.boundingBox;
  if (!box || box.width < 8 || box.height < 8) return null;
  const sx = liveSize.width / (videoEl.videoWidth || liveSize.width);
  const sy = liveSize.height / (videoEl.videoHeight || liveSize.height);
  return {
    x: box.x * sx,
    y: box.y * sy,
    width: box.width * sx,
    height: box.height * sy,
  };
}

export async function detectServerFaceBox(
  http: HttpClient,
  videoEl: HTMLVideoElement,
  liveSize: { width: number; height: number },
  enrollDetectCanvas: HTMLCanvasElement,
): Promise<SmoothBox | null> {
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
  if (!ctx) return null;
  ctx.drawImage(videoEl, 0, 0, w, h);
  const blob = await new Promise<Blob | null>((resolve) =>
    enrollDetectCanvas.toBlob((b) => resolve(b), 'image/jpeg', 0.7),
  );
  if (!blob) return null;
  const form = new FormData();
  form.append('file', blob, 'enroll-detect.jpg');
  const res = await firstValueFrom(
    http.post<{
      faces?: Array<{ x: number; y: number; width: number; height: number; score?: number }>;
      frameWidth?: number;
      frameHeight?: number;
    }>(environment.baseUrl + '/face/detect', form),
  );
  const face = res?.faces?.[0];
  if (!face || face.width < 8 || face.height < 8) return null;
  const fw = res.frameWidth || w;
  const fh = res.frameHeight || h;
  const sx = liveSize.width / fw;
  const sy = liveSize.height / fh;
  return {
    x: face.x * sx,
    y: face.y * sy,
    width: face.width * sx,
    height: face.height * sy,
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
