import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { RouterModule, RouterOutlet, provideRouter } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations'

import { App_Route } from './app.routes';
import { ColorPickerModule, ColorPickerService } from 'ngx-color-picker';
import { CalendarModule, DateAdapter } from 'angular-calendar';
import { adapterFactory } from 'angular-calendar/date-adapters/date-fns';
import { ToastrModule } from 'ngx-toastr';
import { NgDragDropModule } from 'ng-drag-drop';
import { HTTP_INTERCEPTORS, provideHttpClient, HttpClient, withInterceptorsFromDi } from "@angular/common/http";
import { HttpRequestInterceptor } from './shared/services/http-request.interceptor';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { TranslateHttpLoader } from '@ngx-translate/http-loader';
import { provideEcharts } from 'ngx-echarts';

export function HttpLoaderFactory(http: HttpClient) {
  return new TranslateHttpLoader(http, "./assets/i18n/", ".json");
}

export const provideTranslation = () => ({
  defaultLanguage: 'th',
  loader: {
    provide: TranslateLoader,
    useFactory: HttpLoaderFactory,
    deps: [HttpClient],
  },
});

export const httpInterceptorProviders = [
  {
    provide: HTTP_INTERCEPTORS,
    useClass: HttpRequestInterceptor,
    multi: true,
  }
];

export const appConfig: ApplicationConfig = {
  providers: [provideHttpClient(withInterceptorsFromDi()), provideRouter(App_Route), RouterOutlet, ColorPickerModule, ColorPickerService, provideAnimations(),
  importProvidersFrom(RouterModule.forRoot(App_Route, { initialNavigation: 'enabledNonBlocking', useHash: true }), TranslateModule.forRoot(provideTranslation()), CalendarModule.forRoot({
    provide: DateAdapter,
    useFactory: adapterFactory,
  }), ToastrModule.forRoot({
    timeOut: 15000, // 15 seconds
    closeButton: true,
    progressBar: true,
  }), NgDragDropModule.forRoot()),
    httpInterceptorProviders,
    provideEcharts(),
  ]
};



