// This file can be replaced during build by using the `fileReplacements` array.
// `ng build` replaces `environment.ts` with `environment.prod.ts`.
// The list of file replacements can be found in `angular.json`.
//
// SECRETS POLICY
// - Never commit real API keys here; environment files are bundled into the public SPA.
// - Google Maps API key / Map ID come from `assets/config.json` at runtime
//   (copy `assets/config.example.json` → `assets/config.json` for local dev; it is git-ignored).
// - Firebase is NOT used by the app (`@angular/fire` was removed). The block below is a schema placeholder
//   only; see environment.prod.ts and docs/SECRETS-REMEDIATION.md for how to inject values per environment.
export const environment = {
  production: false,
  baseUrl: 'http://localhost:8000',
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

/*
 * For easier debugging in development mode, you can import the following file
 * to ignore zone related error stack frames such as `zone.run`, `zoneDelegate.invokeTask`.
 *
 * This import should be commented out in production mode because it will have a negative impact
 * on performance if an error is thrown.
 */
// import 'zone.js/plugins/zone-error';  // Included with Angular CLI.
