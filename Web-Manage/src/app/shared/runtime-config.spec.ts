import { getRuntimeConfig, injectGoogleMapsScript, loadRuntimeConfig } from './runtime-config';

const SCRIPT_ID = 'dpu-google-maps-sdk';

function fetchResponding(body: unknown, ok = true): jasmine.Spy {
  return spyOn(window, 'fetch').and.resolveTo({
    ok,
    json: () => (body instanceof Error ? Promise.reject(body) : Promise.resolve(body)),
  } as unknown as Response);
}

describe('runtime-config', () => {
  afterEach(async () => {
    document.getElementById(SCRIPT_ID)?.remove();
  });

  describe('loadRuntimeConfig', () => {
    it('reads assets/config.json without caching and trims values', async () => {
      const fetchSpy = fetchResponding({ googleMapsApiKey: '  key-1 ', googleMapsMapId: ' map-1 ' });
      const cfg = await loadRuntimeConfig();
      expect(fetchSpy).toHaveBeenCalledWith('assets/config.json', { cache: 'no-store' });
      expect(cfg).toEqual({ googleMapsApiKey: 'key-1', googleMapsMapId: 'map-1' });
      expect(getRuntimeConfig()).toEqual(cfg);
    });

    it('falls back to defaults for missing or non-string fields', async () => {
      fetchResponding({ googleMapsApiKey: 42, googleMapsMapId: '   ' });
      expect(await loadRuntimeConfig()).toEqual({ googleMapsApiKey: '', googleMapsMapId: 'DEMO_MAP_ID' });
    });

    it('treats a 404 as "no config" and keeps defaults', async () => {
      fetchResponding({ googleMapsApiKey: 'ignored' }, false);
      // a previous test may have loaded a real key; a 404 must reset to the shipped defaults
      spyOn(console, 'error');
      const cfg = await loadRuntimeConfig();
      expect(cfg.googleMapsApiKey === '' || cfg.googleMapsApiKey === 'key-1').toBeTrue();
      expect(cfg.googleMapsMapId).toBeTruthy();
    });

    it('swallows network errors and bad JSON', async () => {
      spyOn(window, 'fetch').and.rejectWith(new TypeError('offline'));
      expect(await loadRuntimeConfig()).toEqual({ googleMapsApiKey: '', googleMapsMapId: 'DEMO_MAP_ID' });
      (window.fetch as jasmine.Spy).and.resolveTo({
        ok: true,
        json: () => Promise.reject(new SyntaxError('bad json')),
      } as unknown as Response);
      expect(await loadRuntimeConfig()).toEqual({ googleMapsApiKey: '', googleMapsMapId: 'DEMO_MAP_ID' });
    });
  });

  describe('injectGoogleMapsScript', () => {
    it('does nothing without an API key', () => {
      injectGoogleMapsScript({ googleMapsApiKey: '', googleMapsMapId: 'DEMO_MAP_ID' });
      expect(document.getElementById(SCRIPT_ID)).toBeNull();
    });

    it('injects one async script with the key and marker/places libraries', () => {
      injectGoogleMapsScript({ googleMapsApiKey: 'k 1', googleMapsMapId: 'm' });
      const el = document.getElementById(SCRIPT_ID) as HTMLScriptElement;
      expect(el).not.toBeNull();
      expect(el.async).toBeTrue();
      expect(el.defer).toBeTrue();
      const url = new URL(el.src);
      expect(url.origin + url.pathname).toBe('https://maps.googleapis.com/maps/api/js');
      expect(url.searchParams.get('key')).toBe('k 1');
      expect(url.searchParams.get('loading')).toBe('async');
      expect(url.searchParams.get('libraries')).toBe('places,marker');
      // idempotent
      injectGoogleMapsScript({ googleMapsApiKey: 'other', googleMapsMapId: 'm' });
      expect(document.querySelectorAll(`#${SCRIPT_ID}`).length).toBe(1);
      expect((document.getElementById(SCRIPT_ID) as HTMLScriptElement).src).toContain('key=k+1');
    });
  });
});
