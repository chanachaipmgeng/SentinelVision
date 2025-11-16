import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

export const admin: Routes = [
 {path:'uielements',children:[ {
  path: 'alerts',
  loadComponent: () =>
    import('./alerts/alerts.component').then((m) => m.AlertsComponent),
},
{
  path: 'breadcrumb',
  loadComponent: () =>
    import('./breadcrumb/breadcrumb.component').then((m) => m.BreadcrumbComponent),
},
{
  path: 'buttongroup',
  loadComponent: () =>
    import('./buttongroup/buttongroup.component').then((m) => m.ButtongroupComponent),
},
{
  path: 'buttons',
  loadComponent: () =>
    import('./buttons/buttons.component').then((m) => m.ButtonsComponent),
},
{
  path: 'badge',
  loadComponent: () =>
    import('./badge/badge.component').then(
      (m) => m.BadgeComponent
    ),
},
{
  path: 'buttongroup',
  loadComponent: () =>
    import('./buttongroup/buttongroup.component').then(
      (m) => m.ButtongroupComponent
    ),
},
{
  path: 'cards',
  loadComponent: () =>
    import('./cards/cards.component').then((m) => m.CardsComponent),
},
{
  path: 'dropdowns',
  loadComponent: () =>
    import('./dropdowns/dropdowns.component').then((m) => m.DropdownsComponent),
},
{
  path: 'images-figures',
  loadComponent: () =>
    import('./images-figures/images-figures.component').then((m) => m.ImagesFiguresComponent),
},
{
  path: 'indicators',
  loadComponent: () =>
    import('./indicators/indicators.component').then((m) => m.IndicatorsComponent),
},
{
  path: 'listgroup',
  loadComponent: () =>
    import('./listgroup/listgroup.component').then((m) => m.ListgroupComponent),
},
{
  path: 'navtabs',
  loadComponent: () =>
    import('./navtabs/navtabs.component').then((m) => m.NavtabsComponent),
},
{
  path: 'objectfit',
  loadComponent: () =>
    import('./objectfit/objectfit.component').then((m) => m.ObjectfitComponent),
},
{
  path: 'pagination',
  loadComponent: () =>
    import('./pagination/pagination.component').then((m) => m.PaginationComponent),
},
{
  path: 'popovers',
  loadComponent: () =>
    import('./popovers/popovers.component').then((m) => m.PopoversComponent),
},
{
  path: 'toasts',
  loadComponent: () =>
    import('./toasts/toasts.component').then((m) => m.ToastsComponent),
},
{
  path: 'progress',
  loadComponent: () =>
    import('./progress/progress.component').then((m) => m.ProgressComponent),
},
{
    path: 'spinners',
    loadComponent: () =>
      import('./spinners/spinners.component').then((m) => m.SpinnersComponent),
  },
  {
    path: 'toasts',
    loadComponent: () =>
      import('./toasts/toasts.component').then((m) => m.ToastsComponent),
  },
  {
    path: 'tooltips',
    loadComponent: () =>
      import('./tooltips/tooltips.component').then((m) => m.TooltipsComponent),
  },
]}
];
@NgModule({
  imports: [RouterModule.forChild(admin)],
  exports: [RouterModule],
})
export class uielementsRoutingModule {
  static routes = admin;
}