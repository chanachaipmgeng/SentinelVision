#!/usr/bin/env node
/**
 * Copy ONNX Runtime WASM assets into Web-Manage/public/ort for same-origin loading.
 */
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const srcDir = path.join(root, 'node_modules', 'onnxruntime-web', 'dist');
const outDir = path.join(root, 'public', 'ort');

const files = [
  'ort-wasm-simd-threaded.wasm',
  'ort-wasm-simd-threaded.mjs',
  'ort-wasm-simd-threaded.jsep.wasm',
  'ort-wasm-simd-threaded.jsep.mjs',
];

fs.mkdirSync(outDir, { recursive: true });
for (const name of files) {
  const from = path.join(srcDir, name);
  const to = path.join(outDir, name);
  if (!fs.existsSync(from)) {
    console.warn('Missing', from);
    continue;
  }
  fs.copyFileSync(from, to);
  console.log('Copied', name, fs.statSync(to).size, 'bytes');
}
