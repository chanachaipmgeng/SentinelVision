#!/usr/bin/env node
/**
 * Copy MediaPipe Tasks Vision WASM into Web-Manage/public/mediapipe (same-origin).
 * Do not rename files — FilesetResolver expects the upstream names.
 */
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const srcDir = path.join(root, 'node_modules', '@mediapipe', 'tasks-vision', 'wasm');
const outDir = path.join(root, 'public', 'mediapipe');

if (!fs.existsSync(srcDir)) {
  console.error('Missing', srcDir, '— run npm install in Web-Manage first');
  process.exit(1);
}

fs.mkdirSync(outDir, { recursive: true });
const names = fs.readdirSync(srcDir);
let copied = 0;
for (const name of names) {
  const from = path.join(srcDir, name);
  if (!fs.statSync(from).isFile()) {
    continue;
  }
  const to = path.join(outDir, name);
  fs.copyFileSync(from, to);
  console.log('Copied', name, fs.statSync(to).size, 'bytes');
  copied += 1;
}
if (!copied) {
  console.error('No files copied from', srcDir);
  process.exit(1);
}
