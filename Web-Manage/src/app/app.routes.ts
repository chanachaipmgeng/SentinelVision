import { Route } from '@angular/router';
import { ContentLayoutComponent } from './shared/layouts/content-layout/content-layout.component';
import { content } from './shared/routes/content.routes';
import { AuthenticationLayoutComponent } from './shared/layouts/authentication-layout/authentication-layout.component';
import { authen } from './shared/routes/auth.routes';
import { landingRoutingModule } from './components/pages/landing.routes';
import { landing } from './shared/routes/landing.routes';
import { LandingLayoutComponent } from './shared/layouts/landing-layout/landing-layout.component';
import { AuthGuard } from './shared/services/auth.guard';
import { LoginComponent } from './authentication/login/login.component';
import { CoverComponent } from './components/authentication/reset-password/cover/cover.component';

export const App_Route: Route[] = [
  { path: '', redirectTo: 'auth/login', pathMatch: 'full' },
  { path: '', component: ContentLayoutComponent, children: content},

  {
    path: 'auth/login',
    component: LoginComponent
  },
  {
    path: 'auth/reset-password',
    component: CoverComponent
  }
]
