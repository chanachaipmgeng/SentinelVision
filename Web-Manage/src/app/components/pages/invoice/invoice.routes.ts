      import { NgModule } from '@angular/core';
      import { RouterModule, Routes } from '@angular/router';
      
      export const admin: Routes = [
       {path:'pages/invoice',children:[ {
        path: 'create-invoice',
        loadComponent: () =>
          import('./create-invoice/create-invoice.component').then((m) => m.CreateInvoiceComponent),
      },
      {
        path: 'invoice-details',
        loadComponent: () =>
          import('./invoice-details/invoice-details.component').then(
            (m) => m.InvoiceDetailsComponent
          ),
      },
      {
        path: 'invoice-list',
        loadComponent: () =>
          import('./invoice-list/invoice-list.component').then(
            (m) => m.InvoiceListComponent
          ),
      },
     
 
      
      ]}
      ];
      @NgModule({
        imports: [RouterModule.forChild(admin)],
        exports: [RouterModule],
      })
      export class invoiceRoutingModule {
        static routes = admin;
      }