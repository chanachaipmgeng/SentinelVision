// Production build (`ng build --configuration=production` replaces environment.ts with this file).
//
// SECRETS POLICY
// - Never commit real API keys here. This file is public in the built bundle AND in git history.
// - Map ID is read at runtime from `assets/config.json`, written by the nginx entrypoint
//   from GOOGLE_MAPS_MAP_ID. The Maps browser key is always empty
//   (see Web-Manage/docker/40-runtime-config.sh and docs/SECRETS-REMEDIATION.md).
// - Firebase is NOT used by the app (`@angular/fire` was removed). The block below is kept only as a
//   schema placeholder. If Firebase is ever re-enabled, inject the values per environment at build time
//   (CI `fileReplacements` with a generated file, or `envsubst` over a template) — do not paste them here.
export const environment = {
  production: true,
  baseUrl: '',
  /** Fallback only; runtime `assets/config.json` → `googleMapsMapId` takes precedence. */
  googleMapsMapId: 'DEMO_MAP_ID',
  firebase: {
    apiKey: '',
    authDomain: '',
    projectId: '',
    storageBucket: '',
    messagingSenderId: '',
    appId: '',
    measurementId: '',
  },
};
