import { Routes } from '@angular/router';
import { CommonManageModule } from '../../DPU/common/common.module';
import { CompanyManagementModule } from '../../DPU/company-management/company-management.module';

const errorPage = () =>
  import('../components/error-page/error-page.component').then((m) => m.ErrorPageComponent);

export const content: Routes = [
  { path: 'error/403', loadComponent: errorPage, data: { code: '403' } },
  { path: 'error/404', loadComponent: errorPage, data: { code: '404' } },
  { path: 'error/500', loadComponent: errorPage, data: { code: '500' } },
  {
    path: '',
    children: [
      ...CommonManageModule.routes,
      ...CompanyManagementModule.routes,
    ],
  },
];
