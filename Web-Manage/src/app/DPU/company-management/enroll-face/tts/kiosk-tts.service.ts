/**
 * Kiosk TTS: settings-aware check-in speech on top of shared SpeechSynthesis helpers.
 */
import { speakText, unlockSpeech, TtsSpeakOptions } from '../../../../shared/utils/tts';
import {
  TtsSettings,
  TtsTemplateKey,
  TtsTemplateVars,
  buildSpeechText,
  resolveTtsSettings,
} from '../../../../shared/utils/tts-templates';

export { speakText, unlockSpeech, buildSpeechText, resolveTtsSettings };
export type { TtsSettings, TtsTemplateKey, TtsTemplateVars };

/** Pure utterance builder — unit-tested without touching SpeechSynthesis. */
export type CheckInUtterance = {
  text: string;
  lang: string;
  rate: number;
  pitch: number;
};

export function buildCheckInUtterance(
  settings: TtsSettings,
  key: TtsTemplateKey,
  vars: TtsTemplateVars = {},
): CheckInUtterance | null {
  const text = buildSpeechText(settings, key, vars);
  if (!text) {
    return null;
  }
  return {
    text,
    lang: settings.lang,
    rate: settings.rate,
    pitch: settings.pitch,
  };
}

/** Speak a check-in template using cached company TTS settings. */
export function speakCheckIn(
  settings: TtsSettings,
  key: TtsTemplateKey,
  vars: TtsTemplateVars = {},
  speak: (text: string, opts?: TtsSpeakOptions) => void = speakText,
): void {
  const utterance = buildCheckInUtterance(settings, key, vars);
  if (!utterance) {
    return;
  }
  speak(utterance.text, {
    lang: utterance.lang,
    rate: utterance.rate,
    pitch: utterance.pitch,
    cancelPrevious: true,
  });
}
