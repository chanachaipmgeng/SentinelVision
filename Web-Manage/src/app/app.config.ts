import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { RouterModule, RouterOutlet, provideRouter } from '@angular/router';
import { BrowserAnimationsModule, provideAnimations } from '@angular/platform-browser/animations'
import { BrowserModule } from '@angular/platform-browser'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'

import { App_Route } from './app.routes';
import { ColorPickerModule, ColorPickerService } from 'ngx-color-picker';
import { CalendarModule, DateAdapter } from 'angular-calendar';
import { adapterFactory } from 'angular-calendar/date-adapters/date-fns';
import { AngularFireModule } from '@angular/fire/compat';
import { environment } from '../environments/environment';
import { AngularFireAuthModule } from '@angular/fire/compat/auth';
import { AngularFireDatabaseModule } from '@angular/fire/compat/database';
import { AngularFirestoreModule } from '@angular/fire/compat/firestore';
import { ToastrModule } from 'ngx-toastr';
import { NgDragDropModule } from 'ng-drag-drop';
import { HttpClientModule, HTTP_INTERCEPTORS, provideHttpClient, HttpClient, withInterceptors } from "@angular/common/http";
import { HttpRequestInterceptor } from './shared/services/http-request.interceptor';
import { AuthService } from './shared/services/auth.service';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { TranslateHttpLoader } from '@ngx-translate/http-loader';

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
  providers: [provideHttpClient(withInterceptors([])), provideRouter(App_Route), RouterOutlet, ColorPickerModule, ColorPickerService, provideAnimations(), AngularFireModule,
    AngularFireDatabaseModule,
    AngularFirestoreModule,
    AngularFireAuthModule,
  importProvidersFrom(RouterModule.forRoot(App_Route, { initialNavigation: 'enabledNonBlocking', useHash: true }), TranslateModule.forRoot(provideTranslation()), CalendarModule.forRoot({
    provide: DateAdapter,
    useFactory: adapterFactory,
  }), AngularFireModule.initializeApp(environment.firebase), ToastrModule.forRoot({
    timeOut: 15000, // 15 seconds
    closeButton: true,
    progressBar: true,
  }), NgDragDropModule.forRoot(), HttpClientModule),
    httpInterceptorProviders,
  ]
};



