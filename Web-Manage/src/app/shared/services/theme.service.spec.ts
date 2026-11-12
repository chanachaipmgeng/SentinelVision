import { TestBed } from '@angular/core/testing';
import { DENSITY_STORAGE_KEY, THEME_STORAGE_KEY, ThemeService } from './theme.service';

describe('ThemeService', () => {
  const html = document.documentElement;

  const fresh = (): ThemeService => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({});
    return TestBed.inject(ThemeService);
  };

  beforeEach(() => {
    localStorage.removeItem(THEME_STORAGE_KEY);
    localStorage.removeItem(DENSITY_STORAGE_KEY);
    html.classList.remove('dark', 'light', 'dpu-kiosk-mode');
    html.removeAttribute('data-theme');
    html.removeAttribute('data-theme-mode');
    html.removeAttribute('data-density');
  });

  afterEach(() => {
    localStorage.removeItem(THEME_STORAGE_KEY);
    localStorage.removeItem(DENSITY_STORAGE_KEY);
    html.classList.remove('dark', 'light', 'dpu-kiosk-mode');
    html.setAttribute('data-theme', 'dark');
    html.removeAttribute('data-density');
  });

  it('defaults to dark and persists the light preference under sv_theme', () => {
    const svc = fresh();
    expect(svc.theme()).toBe('dark');
    expect(html.getAttribute('data-theme')).toBe('dark');

    svc.toggleTheme();
    expect(svc.theme()).toBe('light');
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light');
    expect(html.getAttribute('data-theme')).toBe('light');
    expect(html.getAttribute('data-theme-mode')).toBe('light');
    expect(html.classList.contains('dark')).toBeFalse();
  });

  it('restores the stored preference on startup', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light');
    const svc = fresh();
    expect(svc.theme()).toBe('light');
  });

  it('keeps kiosk light even when dark is preferred', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark');
    const svc = fresh();
    expect(html.getAttribute('data-theme')).toBe('dark');
    expect(svc.effectiveTheme).toBe('dark');

    svc.setShellActive(true);
    expect(svc.effectiveTheme).toBe('dark');

    svc.setKioskActive(true);
    expect(html.getAttribute('data-theme')).toBe('light');
    expect(html.classList.contains('dark')).toBeFalse();

    svc.setKioskActive(false);
    expect(html.getAttribute('data-theme')).toBe('dark');
  });

  it('toggles compact density and persists it under sv_density', () => {
    const svc = fresh();
    svc.setShellActive(true);
    expect(html.hasAttribute('data-density')).toBeFalse();

    svc.toggleDensity();
    expect(svc.density()).toBe('compact');
    expect(localStorage.getItem(DENSITY_STORAGE_KEY)).toBe('compact');
    expect(html.getAttribute('data-density')).toBe('compact');

    svc.toggleDensity();
    expect(html.hasAttribute('data-density')).toBeFalse();
  });
});
