      import { NgModule } from '@angular/core';
      import { RouterModule, Routes } from '@angular/router';
      
      export const admin: Routes = [
       {path:'pages/filemanager',children:[ {
        path: 'filemanager',
        loadComponent: () =>
          import('./filemanager/filemanager.component').then((m) => m.FilemanagerComponent),
      },
     
      ]}
      ];
      @NgModule({
        imports: [RouterModule.forChild(admin)],
        exports: [RouterModule],
      })
      export class filemanagerRoutingModule {
        static routes = admin;
      }