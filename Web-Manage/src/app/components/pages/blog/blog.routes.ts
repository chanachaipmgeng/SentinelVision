     import { NgModule } from '@angular/core';
      import { RouterModule, Routes } from '@angular/router';
      
      export const admin: Routes = [
       {path:'pages/blog',children:[ {
        path: 'blog',
        loadComponent: () =>
          import('./blog/blog.component').then((m) => m.BlogComponent),
      },
      {
        path: 'blog-details',
        loadComponent: () =>
          import('./blog-details/blog-details.component').then(
            (m) => m.BlogDetailsComponent
          ),
      },
      {
        path: 'create-blog',
        loadComponent: () =>
          import('./create-blog/create-blog.component').then(
            (m) => m.CreateBlogComponent
          ),
      },
     
 
      
      ]}
      ];
      @NgModule({
        imports: [RouterModule.forChild(admin)],
        exports: [RouterModule],
      })
      export class blogRoutingModule {
        static routes = admin;
      }