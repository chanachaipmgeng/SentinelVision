import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [
 {path:'maps',children:[ {
  path: 'leafletmaps',
  loadComponent: () =>
    import('./leafletmaps/leafletmaps.component').then((m) => m.LeafletmapsComponent),
},


]}
];
@NgModule({
  imports: [RouterModule.forChild(admin)],
  exports: [RouterModule],
})
export class mapsRoutingModule {
  static routes = admin;
}