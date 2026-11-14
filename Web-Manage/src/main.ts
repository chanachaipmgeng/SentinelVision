import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';
import { injectGoogleMapsScript, loadRuntimeConfig } from './app/shared/runtime-config';

/** After `admin` rebuild, an open tab still holds the old main bundle and
 *  navigates to lazy chunks that no longer exist (404). Reload once so the
 *  fresh index.html + hashed assets load. */
function isStaleChunkError(reason: unknown): boolean {
  const msg = String(
    (reason as { message?: string })?.message || reason || '',
  );
  return /Failed to fetch dynamically imported module|Loading chunk [\w-]+ failed|Importing a module script failed|error loading dynamically imported module/i.test(
    msg,
  );
}

function reloadOnceForStaleChunks(): void {
  const key = 'dpu-chunk-reload-at';
  const last = Number(sessionStorage.getItem(key) || 0);
  if (Date.now() - last < 15_000) {
    return;
  }
  sessionStorage.setItem(key, String(Date.now()));
  window.location.reload();
}

window.addEventListener('unhandledrejection', (event) => {
  if (isStaleChunkError(event.reason)) {
    event.preventDefault();
    reloadOnceForStaleChunks();
  }
});

window.addEventListener('error', (event) => {
  if (isStaleChunkError(event.error) || isStaleChunkError(event.message)) {
    reloadOnceForStaleChunks();
  }
});

loadRuntimeConfig()
  .then((config) => injectGoogleMapsScript(config))
  .then(() => bootstrapApplication(AppComponent, appConfig))
  .catch((err) => console.error(err));
