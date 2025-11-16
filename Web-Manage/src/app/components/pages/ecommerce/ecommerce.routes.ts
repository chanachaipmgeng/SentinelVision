      import { NgModule } from '@angular/core';
      import { RouterModule, Routes } from '@angular/router';
      
      export const admin: Routes = [
       {path:'pages/ecommerce',children:[ {
        path: 'addproduct',
        loadComponent: () =>
          import('./addproduct/addproduct.component').then((m) => m.AddproductComponent),
      },
      {
        path: 'cart',
        loadComponent: () =>
          import('./cart/cart.component').then(
            (m) => m.CartComponent
          ),
      },
      {
        path: 'checkout',
        loadComponent: () =>
          import('./checkout/checkout.component').then(
            (m) => m.CheckoutComponent
          ),
      },
      {
        path: 'editproducts',
        loadComponent: () =>
          import('./editproducts/editproducts.component').then((m) => m.EditproductsComponent),
      },
      {
        path: 'orderdetails',
        loadComponent: () =>
          import('./orderdetails/orderdetails.component').then((m) => m.OrderdetailsComponent),
      },
      {
        path: 'orders',
        loadComponent: () =>
          import('./orders/orders.component').then((m) => m.OrdersComponent),
      },
      {
        path: 'product-details',
        loadComponent: () =>
          import('./product-details/product-details.component').then((m) => m.ProductDetailsComponent),
      },
      {
        path: 'products',
        loadComponent: () =>
          import('./products/products.component').then((m) => m.ProductsComponent),
      },
      {
        path: 'products-list',
        loadComponent: () =>
          import('./products-list/products-list.component').then((m) => m.ProductsListComponent),
      },
      {
        path: 'wishlist',
        loadComponent: () =>
          import('./wishlist/wishlist.component').then((m) => m.WishlistComponent),
      },
 
      
      ]}
      ];
      @NgModule({
        imports: [RouterModule.forChild(admin)],
        exports: [RouterModule],
      })
      export class ecommerceRoutingModule {
        static routes = admin;
      }