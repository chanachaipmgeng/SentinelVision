import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [  
 {path:'authentication',children:[ {
  path: 'commingsoon',
  loadComponent: () =>
    import('./commingsoon/commingsoon.component').then((m) => m.CommingsoonComponent),
},
{
  path: 'under-maintainance',
  loadComponent: () =>
    import('./under-maintainance/under-maintainance.component').then(
      (m) => m.UnderMaintainanceComponent
    ),
},

]}
];
@NgModule({
  imports: [RouterModule.forChild(admin)],
  exports: [RouterModule],
})
export class authenticationRoutingModule {
  static routes = admin;
}