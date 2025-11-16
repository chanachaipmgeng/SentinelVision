     import { NgModule } from '@angular/core';
      import { RouterModule, Routes } from '@angular/router';
      
      export const admin: Routes = [
       {path:'advancedui',children:[ {
        path: 'accordions',
        loadComponent: () =>
          import('./accordions/accordions.component').then((m) => m.AccordionsComponent),
      },
      {
        path: 'draggable-cards',
        loadComponent: () =>
          import('./draggable-cards/draggable-cards.component').then(
            (m) => m.DraggableCardsComponent
          ),
      },
      {
        path: 'modals',
        loadComponent: () =>
          import('./modals/modals.component').then(
            (m) => m.ModalsComponent
          ),
      },
      {
        path: 'navbar',
        loadComponent: () =>
          import('./navbar/navbar.component').then((m) => m.NavbarComponent),
      },
      {
        path: 'offcanvas',
        loadComponent: () =>
          import('./offcanvas/offcanvas.component').then((m) => m.OffcanvasComponent),
      },
      {
        path: 'rating',
        loadComponent: () =>
          import('./rating/rating.component').then((m) => m.RatingComponent),
      },
      {
        path: 'scrollspy',
        loadComponent: () =>
          import('./scrollspy/scrollspy.component').then((m) => m.ScrollspyComponent),
      },
      {
        path: 'swiperjs',
        loadComponent: () =>
          import('./swiperjs/swiperjs.component').then((m) => m.SwiperjsComponent),
      },
      
      
      ]}
      ];
      @NgModule({
        imports: [RouterModule.forChild(admin)],
        exports: [RouterModule],
      })
      export class advanceduiRoutingModule {
        static routes = admin;
      }