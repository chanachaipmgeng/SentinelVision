#!/usr/bin/env node
/**
 * Fetch Silero VAD ONNX into Web-Manage/public/models.
 */
const fs = require('fs');
const path = require('path');
const https = require('https');

const outDir = path.join(__dirname, '..', 'public', 'models');
fs.mkdirSync(outDir, { recursive: true });

const MODEL = {
  file: 'silero_vad.onnx',
  url: 'https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx',
};

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
  const outFile = path.join(outDir, MODEL.file);
  if (fs.existsSync(outFile) && fs.statSync(outFile).size > 100_000) {
    console.log('Silero VAD already present:', outFile, fs.statSync(outFile).size, 'bytes');
    return;
  }
  console.log('Downloading', MODEL.url);
  await get(MODEL.url, outFile);
  console.log('Saved', outFile, fs.statSync(outFile).size, 'bytes');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
