 import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [
 {path:'task',children:[ {
  path: 'kanbanboard',
  loadComponent: () =>
    import('./kanbanboard/kanbanboard.component').then((m) => m.KanbanboardComponent),
},
{
  path: 'list-view',
  loadComponent: () =>
    import('./list-view/list-view.component').then(
      (m) => m.ListViewComponent
    ),
},
{
  path: 'task-details',
  loadComponent: () =>
    import('./task-details/task-details.component').then(
      (m) => m.TaskDetailsComponent
    ),
},
]}
];
@NgModule({
  imports: [RouterModule.forChild(admin)],
  exports: [RouterModule],
})
export class taskRoutingModule {
  static routes = admin;
}