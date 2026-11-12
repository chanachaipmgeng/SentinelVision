/** Company TTS template defaults and helpers (browser SpeechSynthesis v1). */

export type TtsTemplateKey =
  | 'checkInSuccess'
  | 'checkInWarning'
  | 'checkInDuplicate'
  | 'accessSuccess'
  | 'accessDuplicate'
  | 'watchlistSuccess'
  | 'watchlistDuplicate'
  | 'visitorSuccess'
  | 'visitorDuplicate'
  | 'eventSuccess'
  | 'eventDuplicate'
  | 'enrollSuccess'
  | 'enrollFailed';

export interface TtsTemplateVars {
  name?: string;
  firstName?: string;
  employeeId?: string;
}

export interface TtsSettings {
  enabled: boolean;
  lang: string;
  rate: number;
  pitch: number;
  templates: Record<TtsTemplateKey, string>;
}

export const DEFAULT_TTS_TEMPLATES: Record<TtsTemplateKey, string> = {
  checkInSuccess: 'ลงเวลาสำเร็จ คุณ{name}',
  checkInWarning: 'บันทึกนอกพื้นที่ คุณ{name}',
  checkInDuplicate: 'คุณ{name} ลงเวลาไปแล้ว',
  accessSuccess: 'อนุญาตผ่าน คุณ{name}',
  accessDuplicate: 'คุณ{name} ผ่านโซนแล้ว',
  watchlistSuccess: 'พบรายชื่อ คุณ{name}',
  watchlistDuplicate: 'คุณ{name} ตรวจแล้ว',
  visitorSuccess: 'เช็คอินผู้มาติดต่อ คุณ{name}',
  visitorDuplicate: 'คุณ{name} เช็คอินแล้ว',
  eventSuccess: 'เช็คอินงาน คุณ{name}',
  eventDuplicate: 'คุณ{name} เช็คอินงานแล้ว',
  enrollSuccess: 'บันทึกใบหน้าสำเร็จ คุณ{name}',
  enrollFailed: 'บันทึกใบหน้าไม่สำเร็จ กรุณาลองใหม่',
};

export const DEFAULT_TTS_SETTINGS: TtsSettings = {
  enabled: true,
  lang: 'th-TH',
  rate: 1,
  pitch: 1,
  templates: { ...DEFAULT_TTS_TEMPLATES },
};

export function resolveTtsSettings(raw: unknown): TtsSettings {
  const src =
    raw && typeof raw === 'object' && !Array.isArray(raw)
      ? (raw as Record<string, unknown>)
      : {};
  const templatesSrc =
    src['templates'] && typeof src['templates'] === 'object' && !Array.isArray(src['templates'])
      ? (src['templates'] as Record<string, unknown>)
      : {};

  const templates = { ...DEFAULT_TTS_TEMPLATES };
  (Object.keys(DEFAULT_TTS_TEMPLATES) as TtsTemplateKey[]).forEach((key) => {
    const val = templatesSrc[key];
    if (typeof val === 'string' && val.trim()) {
      templates[key] = val.trim();
    }
  });

  const rate = Number(src['rate']);
  const pitch = Number(src['pitch']);
  return {
    enabled: src['enabled'] !== false,
    lang: typeof src['lang'] === 'string' && src['lang'].trim() ? src['lang'].trim() : 'th-TH',
    rate: Number.isFinite(rate) ? Math.min(1.5, Math.max(0.5, rate)) : 1,
    pitch: Number.isFinite(pitch) ? Math.min(2, Math.max(0, pitch)) : 1,
    templates,
  };
}

export function renderTemplate(
  template: string,
  vars: TtsTemplateVars = {},
): string {
  const map: Record<string, string> = {
    name: (vars.name || '').trim(),
    firstName: (vars.firstName || '').trim(),
    employeeId: (vars.employeeId || '').trim(),
  };
  return template.replace(/\{(name|firstName|employeeId)\}/g, (_, key: string) => map[key] ?? '');
}

export function buildSpeechText(
  settings: TtsSettings,
  key: TtsTemplateKey,
  vars?: TtsTemplateVars,
): string | null {
  if (!settings.enabled) {
    return null;
  }
  const tpl = settings.templates[key] || DEFAULT_TTS_TEMPLATES[key];
  const text = renderTemplate(tpl, vars).replace(/\s+/g, ' ').trim();
  return text || null;
}
