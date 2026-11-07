import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';
import { injectGoogleMapsScript, loadRuntimeConfig } from './app/shared/runtime-config';

loadRuntimeConfig()
  .then((config) => injectGoogleMapsScript(config))
  .then(() => bootstrapApplication(AppComponent, appConfig))
  .catch((err) => console.error(err));
