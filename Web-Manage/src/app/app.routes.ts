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
    path: 'auth/change-password',
    canActivate: [AuthGuard],
    loadComponent: () =>
      import('./authentication/change-password/change-password.component').then((m) => m.ChangePasswordComponent),
  },
];
