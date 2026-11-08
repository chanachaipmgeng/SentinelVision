/** Axis-aligned face box in display (canvas) coordinates. */
export interface SmoothBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** Intersection-over-union of two boxes. */
export function iou(a: SmoothBox, b: SmoothBox): number {
  const x1 = Math.max(a.x, b.x);
  const y1 = Math.max(a.y, b.y);
  const x2 = Math.min(a.x + a.width, b.x + b.width);
  const y2 = Math.min(a.y + a.height, b.y + b.height);
  const inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
  const union = a.width * a.height + b.width * b.height - inter;
  return union > 0 ? inter / union : 0;
}

export function boxCenterDist(a: SmoothBox, b: SmoothBox): number {
  const ax = a.x + a.width / 2;
  const ay = a.y + a.height / 2;
  const bx = b.x + b.width / 2;
  const by = b.y + b.height / 2;
  return Math.hypot(ax - bx, ay - by);
}

export function boxDiagonal(b: SmoothBox): number {
  return Math.hypot(b.width, b.height);
}

/**
 * Ease toward the target around the face center so expand/shrink
 * stays locked on the subject instead of sliding from the top-left.
 */
export function lerpBox(
  prev: SmoothBox,
  next: SmoothBox,
  posT: number,
  sizeT: number,
): SmoothBox {
  const pcx = prev.x + prev.width * 0.5;
  const pcy = prev.y + prev.height * 0.5;
  const ncx = next.x + next.width * 0.5;
  const ncy = next.y + next.height * 0.5;
  const cx = pcx + (ncx - pcx) * posT;
  const cy = pcy + (ncy - pcy) * posT;
  const width = prev.width + (next.width - prev.width) * sizeT;
  const height = prev.height + (next.height - prev.height) * sizeT;
  return {
    x: cx - width * 0.5,
    y: cy - height * 0.5,
    width,
    height,
  };
}

/**
 * Combined IoU + center proximity. Returns 0 when neither criterion matches.
 * Higher is better; used only for ranking among candidates that pass thresholds.
 */
export function matchScore(
  a: SmoothBox,
  b: SmoothBox,
  opts: { iouMatchMin: number; centerMatchMax: number },
): number {
  const overlap = iou(a, b);
  if (overlap >= opts.iouMatchMin) {
    return 1 + overlap;
  }
  const diag = (boxDiagonal(a) + boxDiagonal(b)) / 2;
  if (diag <= 1) {
    return 0;
  }
  const norm = boxCenterDist(a, b) / diag;
  if (norm <= opts.centerMatchMax) {
    return 0.5 + (1 - norm / opts.centerMatchMax) * 0.5;
  }
  return 0;
}

/** Drop overlapping detections so one face cannot spawn multiple tracks. */
export function nmsBoxes(boxes: SmoothBox[], iouThresh: number): SmoothBox[] {
  if (boxes.length <= 1) {
    return boxes;
  }
  const sorted = [...boxes].sort((a, b) => b.width * b.height - a.width * a.height);
  const kept: SmoothBox[] = [];
  for (const box of sorted) {
    if (kept.every((k) => iou(k, box) < iouThresh)) {
      kept.push(box);
    }
  }
  return kept;
}
