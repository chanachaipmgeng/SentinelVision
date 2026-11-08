import { Inject, Injectable, signal } from '@angular/core';
import { DOCUMENT } from '@angular/common';

export type ThemeMode = 'light' | 'dark';
export type DensityMode = 'comfortable' | 'compact';

export const THEME_STORAGE_KEY = 'sv_theme';
export const DENSITY_STORAGE_KEY = 'sv_density';
const KIOSK_MODE_CLASS = 'dpu-kiosk-mode';

/**
 * Shell theme + density preferences.
 *
 * Dark mode only paints while the admin shell (content-layout) is mounted and
 * the kiosk is not active, so login / kiosk pairing / kiosk fullscreen stay light.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly theme = signal<ThemeMode>('light');
  readonly density = signal<DensityMode>('comfortable');

  private shellActive = false;
  private kioskActive = false;

  constructor(@Inject(DOCUMENT) private document: Document) {
    this.theme.set(this.readTheme());
    this.density.set(this.readDensity());
    this.apply();
  }

  /** Effective theme painted on <html> right now (may differ from the preference). */
  get effectiveTheme(): ThemeMode {
    return this.theme() === 'dark' && this.shellActive && !this.kioskActive ? 'dark' : 'light';
  }

  setTheme(mode: ThemeMode): void {
    this.theme.set(mode === 'dark' ? 'dark' : 'light');
    this.write(THEME_STORAGE_KEY, this.theme());
    this.apply();
  }

  toggleTheme(): void {
    this.setTheme(this.theme() === 'dark' ? 'light' : 'dark');
  }

  setDensity(mode: DensityMode): void {
    this.density.set(mode === 'compact' ? 'compact' : 'comfortable');
    this.write(DENSITY_STORAGE_KEY, this.density());
    this.apply();
  }

  toggleDensity(): void {
    this.setDensity(this.density() === 'compact' ? 'comfortable' : 'compact');
  }

  /** Called by the content layout on init/destroy. */
  setShellActive(active: boolean): void {
    this.shellActive = active;
    this.apply();
  }

  /** Called by the content layout whenever kiosk fullscreen toggles. */
  setKioskActive(active: boolean): void {
    this.kioskActive = active;
    this.apply();
  }

  apply(): void {
    const html = this.document?.documentElement;
    if (!html) return;
    const kiosk = this.kioskActive || html.classList.contains(KIOSK_MODE_CLASS);
    const dark = this.theme() === 'dark' && this.shellActive && !kiosk;

    html.setAttribute('data-theme', dark ? 'dark' : 'light');
    html.setAttribute('data-theme-mode', dark ? 'dark' : 'light');
    html.classList.toggle('dark', dark);
    html.classList.toggle('light', !dark);

    if (this.density() === 'compact' && this.shellActive && !kiosk) {
      html.setAttribute('data-density', 'compact');
    } else {
      html.removeAttribute('data-density');
    }
  }

  private readTheme(): ThemeMode {
    return this.read(THEME_STORAGE_KEY) === 'dark' ? 'dark' : 'light';
  }

  private readDensity(): DensityMode {
    return this.read(DENSITY_STORAGE_KEY) === 'compact' ? 'compact' : 'comfortable';
  }

  private read(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  private write(key: string, value: string): void {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* storage disabled (private mode) — preference stays in memory */
    }
  }
}
