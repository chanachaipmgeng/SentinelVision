import { Routes } from '@angular/router';
import { CommonManageModule } from '../../DPU/common/common.module';
import { CompanyManagementModule } from '../../DPU/company-management/company-management.module';

export const content: Routes = [
  {
    path: '',
    children: [
      ...CommonManageModule.routes,
      ...CompanyManagementModule.routes,
    ],
  },
];
