import { dataURLtoFile, scaleDetectionBoxes } from './kiosk-camera';

describe('kiosk-camera helpers', () => {
  describe('scaleDetectionBoxes', () => {
    it('maps frame coords into display space', () => {
      const boxes = scaleDetectionBoxes(
        [{ x: 10, y: 20, width: 40, height: 50 }],
        100,
        100,
        200,
        400,
      );
      expect(boxes).toEqual([{ x: 20, y: 80, width: 80, height: 200 }]);
    });

    it('tolerates empty faces', () => {
      expect(scaleDetectionBoxes([], 480, 360, 640, 480)).toEqual([]);
    });
  });

  describe('dataURLtoFile', () => {
    it('builds a File from a tiny PNG data URL', () => {
      // 1×1 transparent PNG
      const dataUrl =
        'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';
      const file = dataURLtoFile(dataUrl, 'face.png');
      expect(file.name).toBe('face.png');
      expect(file.type).toBe('image/png');
      expect(file.size).toBeGreaterThan(0);
    });
  });
});
