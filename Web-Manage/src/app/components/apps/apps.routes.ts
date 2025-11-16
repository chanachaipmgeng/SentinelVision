import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [
 {path:'apps',children:[ {
  path: 'fullcalender',
  loadComponent: () =>
    import('./fullcalender/fullcalender.component').then((m) => m.FullcalenderComponent),
},
{
    path: 'gallery',
    loadComponent: () =>
      import('./gallery/gallery.component').then((m) => m.GalleryComponent),
  },

]}
];
@NgModule({
  imports: [RouterModule.forChild(admin)],
  exports: [RouterModule],
})
export class appsRoutingModule {
  static routes = admin;
}