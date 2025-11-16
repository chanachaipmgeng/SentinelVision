import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [  
 {path:'authentication/create-password',children:[ {
  path: 'basic',
  loadComponent: () =>
    import('./basic/basic.component').then((m) => m.BasicComponent),
},
{
  path: 'cover',
  loadComponent: () =>
    import('./cover/cover.component').then(
      (m) => m.CoverComponent
    ),
},

]}
];
@NgModule({
  imports: [RouterModule.forChild(admin)],
  exports: [RouterModule],
})
export class createpasswordRoutingModule {
  static routes = admin;
}