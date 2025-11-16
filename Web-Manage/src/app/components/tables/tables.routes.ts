import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [
 {path:'tables',children:[ {
  path: 'data-tables',
  loadComponent: () =>
    import('./data-tables/data-tables.component').then((m) => m.DataTablesComponent),
},
{
    path: 'gridjs-tables',
    loadComponent: () =>
      import('./gridjs-tables/gridjs-tables.component').then((m) => m.GridjsTablesComponent),
  },
  {
    path: 'tables',
    loadComponent: () =>
      import('./tables/tables.component').then((m) => m.TablesComponent),
  },
]}
];
@NgModule({
  imports: [RouterModule.forChild(admin)],
  exports: [RouterModule],
})
export class tablesRoutingModule {
  static routes = admin;
}