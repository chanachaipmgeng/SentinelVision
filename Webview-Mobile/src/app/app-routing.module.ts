import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from './shared/services/auth.guard';
import { ApphomelayoutComponent } from './apphomelayout/apphomelayout.component';

const routes: Routes = [
  {
    path: '',
    component: ApphomelayoutComponent,
    canActivate: [AuthGuard],
    children: [
      {
        path: 'company',
        loadChildren: () =>
          import('./company/company.module').then((m) => m.CompanyModule),
        canActivate: [AuthGuard],
      },
      {
        path: 'general',
        loadChildren: () =>
          import('./general-setting/general-setting.module').then(
            (m) => m.GeneralSettingModule
          ),
        canActivate: [AuthGuard],
      },
      {
        path: 'services',
        loadChildren: () =>
          import('./apps-service-other/apps-service-other.module').then(
            (m) => m.AppsServiceOtherModule
          ),
        canActivate: [AuthGuard],
      },
    ],
  },
  {
    path: '',
    children: [
      {
        path: 'auth',
        loadChildren: () =>
          import('./authlayout/authlayout-routing.module').then(
            (m) => m.AuthlayoutRoutingModule
          ),
      },
    ],
  },
  {
    path: 'signin/AD/:tokenAD',
    redirectTo: 'auth/signin',
  },
  {
    path: '**',
    redirectTo: 'company/home-company',
  },
];

@NgModule({
  imports: [
    RouterModule.forRoot(routes, {
      useHash: true,
      scrollPositionRestoration: 'enabled',
      onSameUrlNavigation: 'reload',
    }),
  ],
  exports: [RouterModule],
})
export class AppRoutingModule {}
