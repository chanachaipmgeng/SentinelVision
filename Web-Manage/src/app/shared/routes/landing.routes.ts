import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { admin, landingRoutingModule } from '../../components/pages/landing.routes';



export const landing: Routes = [

  { path: '', children: [
   ...landingRoutingModule.routes
   
  ]}

  
];
@NgModule({
    imports: [RouterModule.forRoot(admin)],
    exports: [RouterModule]
})
export class landingpageRoutingModule { }
