import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from './shared/services/auth.guard';
import { ApphomelayoutComponent } from './apphomelayout/apphomelayout.component';
import { GeneralSettingComponent } from './general-setting/general-setting.component';

const routes: Routes = [
  {
    path: '',
    children: [
      {
        path: 'company',
        loadChildren: () =>
          import('./company/company.module').then((m) => m.CompanyModule),
        canActivate: [AuthGuard]
      },
      {
        path: 'general',
        loadChildren: () =>
          import('./general-setting/general-setting.module').then((m) => m.GeneralSettingModule),
        canActivate: [AuthGuard]
      },
      {
        path: 'services',
        loadChildren: () =>
          import('./apps-service-other/apps-service-other.module').then((m) => m.AppsServiceOtherModule),
        canActivate: [AuthGuard]
      }
    ],
    component: ApphomelayoutComponent,
    canActivate: [AuthGuard]
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
    path: 'component',
    loadChildren: () =>
      import('./appinnerlayout/appinner-routing.module').then(
        (m) => m.AppinnerlayoutRoutingModule
      )
  },
  {
    path: 'apps',
    component: ApphomelayoutComponent,
    loadChildren: () =>
      import('./apphomelayout/apphome-routing.module').then(
        (m) => m.ApphomelayoutRoutingModule
      )
  },
  {
    path: '**',
    redirectTo: 'component/pagenotfound',
  },
  {
    path: 'signin/AD/:tokenAD',
    redirectTo: 'auth/signin',
  }
];

@NgModule({
  imports: [
    RouterModule.forRoot(routes, {
      // initialNavigation: 'enabled',
      useHash: true,
      scrollPositionRestoration: 'enabled',
      onSameUrlNavigation: 'reload'
    }),
  ],
  exports: [RouterModule]
})
export class AppRoutingModule { }
