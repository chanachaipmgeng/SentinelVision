import { HttpClientModule } from '@angular/common/http';
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [
  //  {path:'auth',children:[ {
  //   path: 'login',
  //   loadComponent: () =>
  //     import('./login/login.component').then((m) => m.LoginComponent),
  // },


  // ]}
];
@NgModule({
  imports: [RouterModule.forChild(admin), HttpClientModule],
  exports: [RouterModule],
})
export class authenticationsRoutingModule {
  static routes = admin;
}
