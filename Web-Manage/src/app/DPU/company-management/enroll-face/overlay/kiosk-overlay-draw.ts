import { SmoothBox } from './kiosk-box';

export type OverlayPalette = {
  stroke: string;
  glow: string;
  labelBg: string;
  labelFg: string;
};

/** Neon scan-frame colors by track state. */
export function overlayPalette(done: boolean, busy: boolean, hasLabel: boolean): OverlayPalette {
  if (done) {
    return {
      stroke: '#67e8f9',
      glow: 'rgba(103, 232, 249, 0.95)',
      labelBg: 'rgba(8, 47, 73, 0.92)',
      labelFg: '#ecfeff',
    };
  }
  if (busy) {
    return {
      stroke: '#7dd3fc',
      glow: 'rgba(125, 211, 252, 0.9)',
      labelBg: 'rgba(12, 74, 110, 0.9)',
      labelFg: '#f0f9ff',
    };
  }
  if (hasLabel) {
    return {
      stroke: '#22d3ee',
      glow: 'rgba(34, 211, 238, 0.95)',
      labelBg: 'rgba(8, 47, 73, 0.9)',
      labelFg: '#ecfeff',
    };
  }
  return {
    stroke: '#38bdf8',
    glow: 'rgba(56, 189, 248, 0.85)',
    labelBg: 'rgba(8, 47, 73, 0.88)',
    labelFg: '#e0f2fe',
  };
}

export function roundRect(
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

/** Draw one neon face frame + optional name/confidence label. */
export function drawSmoothOverlay(
  ctx: CanvasRenderingContext2D,
  box: SmoothBox,
  label: string | null,
  confidence: number | null,
  done: boolean,
  busy: boolean,
): void {
  const pad = 5;
  const x = box.x - pad;
  const y = box.y - pad;
  const w = box.width + pad * 2;
  const h = box.height + pad * 2;
  const radius = 18;
  const { stroke, glow, labelBg, labelFg } = overlayPalette(done, busy, !!label);

  ctx.save();
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 2.75;
  ctx.shadowColor = glow;
  ctx.shadowBlur = 16;
  roundRect(ctx, x, y, w, h, radius);
  ctx.stroke();
  ctx.shadowBlur = 0;

  if (label) {
    const text =
      confidence != null && !busy && !done ? `${label}  ${confidence.toFixed(0)}%` : label;
    ctx.font = '600 14px "Segoe UI", system-ui, sans-serif';
    const metrics = ctx.measureText(text);
    const labelPadX = 10;
    const labelH = 24;
    const labelW = metrics.width + labelPadX * 2;
    const labelX = x;
    const labelY = Math.max(8, y - labelH - 8);

    ctx.shadowColor = glow;
    ctx.shadowBlur = 10;
    ctx.fillStyle = labelBg;
    roundRect(ctx, labelX, labelY, labelW, labelH, 10);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 1;
    roundRect(ctx, labelX, labelY, labelW, labelH, 10);
    ctx.stroke();
    ctx.fillStyle = labelFg;
    ctx.textBaseline = 'middle';
    ctx.fillText(text, labelX + labelPadX, labelY + labelH / 2 + 1);
  }
  ctx.restore();
}
