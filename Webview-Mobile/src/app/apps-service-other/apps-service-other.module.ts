import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppsServiceOtherComponent } from './apps-service-other.component';
import { RouterModule, Routes } from '@angular/router';
const routes: Routes = [
  {
    path: '',
    children: [
      {
        path: '',
        component: AppsServiceOtherComponent,
        data: {
          title: 'Services'
        },
      },
    ]
  }
]
@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild(routes),
  ],
  exports: [RouterModule]
})
export class AppsServiceOtherModule { }
