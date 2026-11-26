#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const i18nDir = path.resolve(__dirname, '..', 'src', 'assets', 'i18n');
const thPath = path.join(i18nDir, 'th.json');
const enPath = path.join(i18nDir, 'en.json');

function flatten(obj, prefix = '', out = {}) {
  for (const [k, v] of Object.entries(obj || {})) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      flatten(v, key, out);
    } else {
      out[key] = v;
    }
  }
  return out;
}

const th = flatten(JSON.parse(fs.readFileSync(thPath, 'utf8')));
const en = flatten(JSON.parse(fs.readFileSync(enPath, 'utf8')));

const thKeys = Object.keys(th);
const enKeys = Object.keys(en);
const missingInEn = thKeys.filter((k) => !(k in en));
const missingInTh = enKeys.filter((k) => !(k in th));
const emptyInTh = thKeys.filter((k) => String(th[k] ?? '').trim() === '');
const emptyInEn = enKeys.filter((k) => String(en[k] ?? '').trim() === '');

if (missingInEn.length || missingInTh.length || emptyInTh.length || emptyInEn.length) {
  console.error('i18n parity check FAILED:');
  if (missingInEn.length) console.error('  Missing in en.json:', missingInEn.slice(0, 20));
  if (missingInTh.length) console.error('  Missing in th.json:', missingInTh.slice(0, 20));
  if (emptyInTh.length) console.error('  Empty values in th.json:', emptyInTh.slice(0, 20));
  if (emptyInEn.length) console.error('  Empty values in en.json:', emptyInEn.slice(0, 20));
  process.exit(1);
}

console.log(`i18n parity check OK: ${thKeys.length} keys matched cleanly across th.json and en.json.`);
