     import { NgModule } from '@angular/core';
      import { RouterModule, Routes } from '@angular/router';
      
      export const admin: Routes = [
       {path:'pages',children:[ {
        path: 'aboutus',
        loadComponent: () =>
          import('./aboutus/aboutus.component').then((m) => m.AboutusComponent),
      },
      {
        path: 'chat',
        loadComponent: () =>
          import('./chat/chat.component').then(
            (m) => m.ChatComponent
          ),
      },
      {
        path: 'contactus',
        loadComponent: () =>
          import('./contactus/contactus.component').then(
            (m) => m.ContactusComponent
          ),
      },
      {
        path: 'contacts',
        loadComponent: () =>
          import('./contacts/contacts.component').then((m) => m.ContactsComponent),
      },
      {
        path: 'emptypage',
        loadComponent: () =>
          import('./emptypage/emptypage.component').then((m) => m.EmptypageComponent),
      },
      {
        path: 'faqs',
        loadComponent: () =>
          import('./faqs/faqs.component').then((m) => m.FaqsComponent),
      },
      {
        path: 'timeline',
        loadComponent: () =>
          import('./timeline/timeline.component').then((m) => m.TimelineComponent),
      },
      {
        path: 'notifications',
        loadComponent: () =>
          import('./notifications/notifications.component').then((m) => m.NotificationsComponent),
      },
      {
        path: 'pricing',
        loadComponent: () =>
          import('./pricing/pricing.component').then((m) => m.PricingComponent),
      },
      {
        path: 'team',
        loadComponent: () =>
          import('./team/team.component').then((m) => m.TeamComponent),
      },
      {
        path: 'terms-conditions',
        loadComponent: () =>
          import('./terms-conditions/terms-conditions.component').then((m) => m.TermsConditionsComponent),
      },
      {
        path: 'todolist',
        loadComponent: () =>
          import('./todolist/todolist.component').then((m) => m.TodolistComponent),
      },
      {
        path: 'profile',
        loadComponent: () =>
          import('./profile/profile.component').then((m) => m.ProfileComponent),
      },
      {
        path: 'reviews',
        loadComponent: () =>
          import('./reviews/reviews.component').then((m) => m.ReviewsComponent),
      },
      ]}
      ];
      @NgModule({
        imports: [RouterModule.forChild(admin)],
        exports: [RouterModule],
      })
      export class pagesRoutingModule {
        static routes = admin;
      }