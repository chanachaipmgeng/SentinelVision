#!/usr/bin/env node
/**
 * Fetch MediaPipe HandLandmarker + GestureRecognizer .task into Web-Manage/public/models.
 */
const fs = require('fs');
const path = require('path');
const https = require('https');

const outDir = path.join(__dirname, '..', 'public', 'models');
fs.mkdirSync(outDir, { recursive: true });

const MODELS = [
  {
    file: 'hand_landmarker.task',
    url: 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
  },
  {
    file: 'gesture_recognizer.task',
    url: 'https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task',
  },
];

function get(target, file, redirects = 0) {
  return new Promise((resolve, reject) => {
    https
      .get(target, (res) => {
        if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          if (redirects > 5) {
            reject(new Error('Too many redirects'));
            return;
          }
          get(res.headers.location, file, redirects + 1).then(resolve, reject);
          return;
        }
        if (res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode} for ${target}`));
          return;
        }
        const stream = fs.createWriteStream(file);
        res.pipe(stream);
        stream.on('finish', () => {
          stream.close();
          resolve();
        });
      })
      .on('error', reject);
  });
}

(async () => {
  for (const model of MODELS) {
    const outFile = path.join(outDir, model.file);
    if (fs.existsSync(outFile) && fs.statSync(outFile).size > 100_000) {
      console.log('Already present:', outFile, fs.statSync(outFile).size, 'bytes');
      continue;
    }
    console.log('Downloading', model.url);
    await get(model.url, outFile);
    console.log('Saved', outFile, fs.statSync(outFile).size, 'bytes');
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
