import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [
 {path:'apps/jobs',children:[ {
  path: 'candidate-details',
  loadComponent: () =>
    import('./candidate-details/candidate-details.component').then((m) => m.CandidateDetailsComponent),
},
{
  path: 'job-details',
  loadComponent: () =>
    import('./job-details/job-details.component').then(
      (m) => m.JobDetailsComponent
    ),
},
{
  path: 'job-post',
  loadComponent: () =>
    import('./job-post/job-post.component').then(
      (m) => m.JobPostComponent
    ),
},
{
    path: 'jobs-list',
    loadComponent: () =>
      import('./jobs-list/jobs-list.component').then(
        (m) => m.JobsListComponent
      ),
  },
  {
    path: 'search-candidate',
    loadComponent: () =>
      import('./search-candidate/search-candidate.component').then(
        (m) => m.SearchCandidateComponent
      ),
  },
  {
    path: 'search-jobs',
    loadComponent: () =>
      import('./search-jobs/search-jobs.component').then(
        (m) => m.SearchJobsComponent
      ),
  },
  {
    path: 'search-company',
    loadComponent: () =>
      import('./search-company/search-company.component').then(
        (m) => m.SearchCompanyComponent
      ),
  },
]}
];
@NgModule({
  imports: [RouterModule.forChild(admin)],
  exports: [RouterModule],
})
export class jobsRoutingModule {
  static routes = admin;
}