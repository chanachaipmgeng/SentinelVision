/**
 * Runtime configuration loaded from `assets/config.json` before Angular bootstraps.
 *
 * The file is NOT committed (see `.gitignore`); `assets/config.example.json` is the
 * template. In Docker the nginx entrypoint (`Web-Manage/docker/40-runtime-config.sh`)
 * writes it from `GOOGLE_MAPS_API_KEY` / `GOOGLE_MAPS_MAP_ID` on every container start,
 * so one image can be deployed to many environments without rebuilding.
 */
export interface RuntimeConfig {
  /** Google Maps JavaScript API key. Empty → Maps script is not loaded, pages use OSM fallback. */
  googleMapsApiKey: string;
  /** Map ID for AdvancedMarkerElement. Defaults to DEMO_MAP_ID. */
  googleMapsMapId: string;
}

const DEFAULT_CONFIG: RuntimeConfig = {
  googleMapsApiKey: '',
  googleMapsMapId: 'DEMO_MAP_ID',
};

const CONFIG_URL = 'assets/config.json';
const MAPS_SCRIPT_ID = 'dpu-google-maps-sdk';

let current: RuntimeConfig = { ...DEFAULT_CONFIG };

export function getRuntimeConfig(): RuntimeConfig {
  return current;
}

/** Fetches `assets/config.json`; any failure (404, bad JSON) falls back to defaults. */
export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  try {
    const res = await fetch(CONFIG_URL, { cache: 'no-store' });
    if (res.ok) {
      const data = (await res.json()) as Partial<RuntimeConfig> | null;
      current = {
        googleMapsApiKey: typeof data?.googleMapsApiKey === 'string' ? data.googleMapsApiKey.trim() : '',
        googleMapsMapId:
          typeof data?.googleMapsMapId === 'string' && data.googleMapsMapId.trim()
            ? data.googleMapsMapId.trim()
            : DEFAULT_CONFIG.googleMapsMapId,
      };
    }
  } catch {
    current = { ...DEFAULT_CONFIG };
  }
  return current;
}

/**
 * Injects the Google Maps JS SDK `<script>` with the configured key.
 * Replaces the former hard-coded tag in `index.html`. No-op when the key is empty
 * or the script is already present. Loading stays async; components keep checking
 * `window.google?.maps?.Map` and `window.__dpuMapsAuthFailed` as before.
 */
export function injectGoogleMapsScript(config: RuntimeConfig = current): void {
  if (!config.googleMapsApiKey || document.getElementById(MAPS_SCRIPT_ID)) {
    return;
  }
  const params = new URLSearchParams({
    key: config.googleMapsApiKey,
    loading: 'async',
    libraries: 'places,marker',
    v: 'weekly',
  });
  const script = document.createElement('script');
  script.id = MAPS_SCRIPT_ID;
  script.src = `https://maps.googleapis.com/maps/api/js?${params.toString()}`;
  script.async = true;
  script.defer = true;
  document.head.appendChild(script);
}
