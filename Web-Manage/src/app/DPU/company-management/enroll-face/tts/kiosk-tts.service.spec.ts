import { buildCheckInUtterance, speakCheckIn, resolveTtsSettings } from './kiosk-tts.service';
import { DEFAULT_TTS_TEMPLATES } from '../../../../shared/utils/tts-templates';

describe('kiosk-tts', () => {
  const settings = resolveTtsSettings(null);

  describe('buildCheckInUtterance', () => {
    it('renders the success template with name', () => {
      const u = buildCheckInUtterance(settings, 'checkInSuccess', { name: 'สมชาย' });
      expect(u).not.toBeNull();
      expect(u!.text).toContain('สมชาย');
      expect(u!.lang).toBe('th-TH');
      expect(u!.rate).toBe(1);
      expect(u!.pitch).toBe(1);
    });

    it('returns null when TTS is disabled', () => {
      const off = resolveTtsSettings({ enabled: false });
      expect(buildCheckInUtterance(off, 'checkInSuccess', { name: 'A' })).toBeNull();
    });

    it('uses duplicate / warning templates', () => {
      const dup = buildCheckInUtterance(settings, 'checkInDuplicate', { name: 'B' });
      expect(dup!.text).toBe(DEFAULT_TTS_TEMPLATES.checkInDuplicate.replace('{name}', 'B'));
      const warn = buildCheckInUtterance(settings, 'checkInWarning', { name: 'C' });
      expect(warn!.text).toBe(DEFAULT_TTS_TEMPLATES.checkInWarning.replace('{name}', 'C'));
    });

    it('honors custom company templates', () => {
      const custom = resolveTtsSettings({
        templates: { checkInSuccess: 'Welcome {firstName}' },
      });
      const u = buildCheckInUtterance(custom, 'checkInSuccess', {
        name: 'Full',
        firstName: 'Sam',
      });
      expect(u!.text).toBe('Welcome Sam');
    });
  });

  describe('speakCheckIn', () => {
    it('forwards utterance options to the speak callback', () => {
      const calls: Array<{ text: string; opts: unknown }> = [];
      speakCheckIn(settings, 'checkInSuccess', { name: 'X' }, (text, opts) => {
        calls.push({ text, opts });
      });
      expect(calls.length).toBe(1);
      expect(calls[0].text).toContain('X');
      expect(calls[0].opts).toEqual(
        jasmine.objectContaining({
          lang: 'th-TH',
          rate: 1,
          pitch: 1,
          cancelPrevious: true,
        }),
      );
    });

    it('does not speak when disabled', () => {
      const calls: string[] = [];
      speakCheckIn(resolveTtsSettings({ enabled: false }), 'checkInSuccess', { name: 'X' }, (t) =>
        calls.push(t),
      );
      expect(calls).toEqual([]);
    });
  });
});
