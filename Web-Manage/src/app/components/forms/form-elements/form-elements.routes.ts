import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [
 {path:'form/forms-elements',children:[ {
  path: 'inputs',
  loadComponent: () =>
    import('./inputs/inputs.component').then((m) => m.InputsComponent),
},
{
  path: 'checksradios',
  loadComponent: () =>
    import('./checksradios/checksradios.component').then(
      (m) => m.ChecksradiosComponent
    ),
},
{
  path: 'inputgroup',
  loadComponent: () =>
    import('./inputgroup/inputgroup.component').then(
      (m) => m.InputgroupComponent
    ),
},
{
    path: 'formselect',
    loadComponent: () =>
      import('./formselect/formselect.component').then(
        (m) => m.FormselectComponent
      ),
  },
  {
    path: 'fileuploads',
    loadComponent: () =>
      import('./fileuploads/fileuploads.component').then(
        (m) => m.FileuploadsComponent
      ),
  },
  
  {
    path: 'datetimepicker',
    loadComponent: () =>
      import('./datetimepicker/datetimepicker.component').then(
        (m) => m.DatetimepickerComponent
      ),
  },
  {
    path: 'colorpicker',
    loadComponent: () =>
      import('./colorpicker/colorpicker.component').then(
        (m) => m.ColorpickerComponent
      ),
  },
  {
    path: 'inputs',
    loadComponent: () =>
      import('./inputs/inputs.component').then(
        (m) => m.InputsComponent
      ),
  },
  {
    path: 'rangeslider',
    loadComponent: () =>
      import('./rangeslider/rangeslider.component').then(
        (m) => m.RangesliderComponent
      ),
  },
]}
];
@NgModule({
  imports: [RouterModule.forChild(admin)],
  exports: [RouterModule],
})
export class formelementsRoutingModule {
  static routes = admin;
}