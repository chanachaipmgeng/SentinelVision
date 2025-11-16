import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [
 {path:'apps/projects',children:[ {
  path: 'create-project',
  loadComponent: () =>
    import('./create-project/create-project.component').then((m) => m.CreateProjectComponent),
},
{
  path: 'project-overview',
  loadComponent: () =>
    import('./project-overview/project-overview.component').then(
      (m) => m.ProjectOverviewComponent
    ),
},
{
  path: 'projectlist',
  loadComponent: () =>
    import('./projectlist/projectlist.component').then(
      (m) => m.ProjectlistComponent
    ),
},

]}
];
@NgModule({
  imports: [RouterModule.forChild(admin)],
  exports: [RouterModule],
})
export class projectsRoutingModule {
  static routes = admin;
}