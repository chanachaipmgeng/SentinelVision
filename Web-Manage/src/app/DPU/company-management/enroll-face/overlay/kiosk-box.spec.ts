import { SmoothBox, iou, lerpBox, matchScore, nmsBoxes } from './kiosk-box';

describe('kiosk-box geometry', () => {
  const box = (x: number, y: number, width: number, height: number): SmoothBox => ({
    x,
    y,
    width,
    height,
  });

  describe('iou', () => {
    it('returns 1 for identical boxes', () => {
      const a = box(10, 10, 40, 40);
      expect(iou(a, a)).toBe(1);
    });

    it('returns 0 for non-overlapping boxes', () => {
      expect(iou(box(0, 0, 10, 10), box(20, 20, 10, 10))).toBe(0);
    });

    it('computes partial overlap', () => {
      // 10×10 overlap of two 20×20 → inter=100, union=700 → ~0.1429
      const score = iou(box(0, 0, 20, 20), box(10, 10, 20, 20));
      expect(score).toBeCloseTo(100 / 700, 5);
    });
  });

  describe('lerpBox', () => {
    it('returns prev when t=0', () => {
      const prev = box(0, 0, 10, 10);
      const next = box(100, 100, 20, 20);
      expect(lerpBox(prev, next, 0, 0)).toEqual(prev);
    });

    it('returns next when t=1', () => {
      const prev = box(0, 0, 10, 10);
      const next = box(100, 50, 20, 30);
      expect(lerpBox(prev, next, 1, 1)).toEqual(next);
    });

    it('eases around center (halfway pos + size)', () => {
      const prev = box(0, 0, 10, 10); // center 5,5
      const next = box(10, 10, 20, 20); // center 20,20
      const mid = lerpBox(prev, next, 0.5, 0.5);
      expect(mid.width).toBeCloseTo(15);
      expect(mid.height).toBeCloseTo(15);
      expect(mid.x + mid.width / 2).toBeCloseTo(12.5);
      expect(mid.y + mid.height / 2).toBeCloseTo(12.5);
    });
  });

  describe('matchScore', () => {
    const opts = { iouMatchMin: 0.12, centerMatchMax: 0.65 };

    it('prefers high IoU matches', () => {
      const a = box(0, 0, 40, 40);
      const near = box(2, 2, 40, 40);
      expect(matchScore(a, near, opts)).toBeGreaterThan(1);
    });

    it('returns 0 when far apart', () => {
      expect(matchScore(box(0, 0, 20, 20), box(200, 200, 20, 20), opts)).toBe(0);
    });
  });

  describe('nmsBoxes', () => {
    it('keeps the larger of two heavily overlapping boxes', () => {
      const kept = nmsBoxes([box(0, 0, 30, 30), box(2, 2, 40, 40)], 0.35);
      expect(kept.length).toBe(1);
      expect(kept[0].width).toBe(40);
    });

    it('keeps non-overlapping boxes', () => {
      const kept = nmsBoxes([box(0, 0, 20, 20), box(100, 100, 20, 20)], 0.35);
      expect(kept.length).toBe(2);
    });
  });
});
