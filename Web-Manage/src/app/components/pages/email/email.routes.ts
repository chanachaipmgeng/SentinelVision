import { Route } from '@angular/router';
import { MailappComponent } from './mailapp/mailapp.component';
import { MailsettingsComponent } from './mailsettings/mailsettings.component';


export default [
    {path:'pages/email',children:[
        {path:'mailapp',component:MailappComponent},
        {path:'mailsettings',component:MailsettingsComponent},
    
      ]}
      ] as Route[];
      import { NgModule } from '@angular/core';
      import { RouterModule, Routes } from '@angular/router';
      
      export const admin: Routes = [
       {path:'pages/email',children:[ {
        path: 'mailapp',
        loadComponent: () =>
          import('./mailapp/mailapp.component').then((m) => m.MailappComponent),
      },
      {
        path: 'mailsettings',
        loadComponent: () =>
          import('./mailsettings/mailsettings.component').then(
            (m) => m.MailsettingsComponent
          ),
      },
    
     
 
      
      ]}
      ];
      @NgModule({
        imports: [RouterModule.forChild(admin)],
        exports: [RouterModule],
      })
      export class mailRoutingModule {
        static routes = admin;
      }