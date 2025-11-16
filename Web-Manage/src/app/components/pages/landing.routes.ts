import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [
 {path:'pages',children:[ {
  path: 'landing',
  loadComponent: () =>
    import('./landing/landing.component').then((m) => m.LandingComponent),
},
{
  path: 'jobs-landing',
  loadComponent: () =>
    import('./jobs-landing/jobs-landing.component').then(
      (m) => m.JobsLandingComponent
    ),
},

]}
];
@NgModule({
  imports: [RouterModule.forChild(admin)],
  exports: [RouterModule],
})
export class landingRoutingModule {
  static routes = admin;
}