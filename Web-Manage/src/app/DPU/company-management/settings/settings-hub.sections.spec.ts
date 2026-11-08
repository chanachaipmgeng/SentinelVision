import {
  SETTINGS_SECTIONS,
  resolveSettingsSection,
  visibleSettingsSections,
} from './settings-hub.sections';

describe('settings hub sections', () => {
  it('shows every section when all permissions are granted', () => {
    const visible = visibleSettingsSections(() => true);
    expect(visible.map((s) => s.id)).toEqual(SETTINGS_SECTIONS.map((s) => s.id));
  });

  it('hides sections whose permission is missing', () => {
    const visible = visibleSettingsSections((code) => code === 'hr.shifts');
    expect(visible.map((s) => s.id)).toEqual(['shifts']);
  });

  it('keeps a valid requested section', () => {
    const visible = visibleSettingsSections(() => true);
    expect(resolveSettingsSection('retention', visible)).toBe('retention');
  });

  it('falls back to notifications for unknown sections', () => {
    const visible = visibleSettingsSections(() => true);
    expect(resolveSettingsSection('nope', visible)).toBe('notifications');
    expect(resolveSettingsSection(null, visible)).toBe('notifications');
  });

  it('falls back to the first visible section when notifications is hidden', () => {
    const visible = visibleSettingsSections((code) => code !== 'notifications.manage');
    expect(resolveSettingsSection('notifications', visible)).toBe('security');
  });

  it('returns null when nothing is visible', () => {
    expect(resolveSettingsSection('notifications', [])).toBeNull();
  });
});
