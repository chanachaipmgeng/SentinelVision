import { Route } from '@angular/router';
import { ContentLayoutComponent } from './shared/layouts/content-layout/content-layout.component';
import { content } from './shared/routes/content.routes';
import { LoginComponent } from './authentication/login/login.component';
import { CoverComponent } from './authentication/reset-password/cover/cover.component';

import { AuthGuard } from './shared/services/auth.guard';

export const App_Route: Route[] = [
  { path: '', redirectTo: 'auth/login', pathMatch: 'full' },
  {
    path: '',
    component: ContentLayoutComponent,
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    children: content,
    data: { animation: 'Content' },
  },
  { path: 'auth/login', component: LoginComponent, data: { animation: 'Login' } },
  { path: 'auth/reset-password', component: CoverComponent, data: { animation: 'ResetPassword' } },
  {
    // Kiosk tablets pair here with a one-time code; no token ever travels in the URL.
    path: 'kiosk/pair',
    loadComponent: () =>
      import('./authentication/kiosk-pair/kiosk-pair.component').then((m) => m.KioskPairComponent),
  },
  {
    path: 'auth/sso/callback',
    loadComponent: () =>
      import('./authentication/sso-callback/sso-callback.component').then((m) => m.SsoCallbackComponent),
  },
  {
    path: 'auth/change-password',
    canActivate: [AuthGuard],
    loadComponent: () =>
      import('./authentication/change-password/change-password.component').then((m) => m.ChangePasswordComponent),
  },
  { path: '**', redirectTo: 'error/404' },
];
