import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CommonComponent } from './common.component';
import { RouterModule, Routes } from '@angular/router';
import { RoleGuard } from '../../shared/services/role.guard';
export const admin: Routes = [
  {
    path: 'admin', canActivate: [RoleGuard], data: { area: 'admin' }, children: [{
      path: 'home',
      loadComponent: () =>
        import('./home-common/home-common.component').then((m) => m.HomeCommonComponent),
    },
    {
      path: 'member-manage',
      loadComponent: () =>
        import('./user-management/user-setting/user-setting.component').then((m) => m.UserSettingComponent),
    },
    {
      path: 'manage-companys',
      loadComponent: () =>
        import('./company-manage/company-manage.component').then((m) => m.CompanyManageComponent),
    },
    {
      path: 'admin-manage',
      loadComponent: () =>
        import('./admin-manage/admin-manage.component').then((m) => m.AdminManageComponent),
    },
    {
      path: 'system-setting',
      loadComponent: () =>
        import('./system-setting/system-setting.component').then((m) => m.SystemSettingComponent),
    },
    {
      path: 'error-logs',
      loadComponent: () =>
        import('./error-logs/error-logs.component').then((m) => m.ErrorLogsComponent),
    },
    //////////////emp/////////////////
    {
      path: 'emp/department',
      loadComponent: () =>
        import('./employee/department/department.component').then((m) => m.DepartmentComponent),
    },
    {
      path: 'emp/position',
      loadComponent: () =>
        import('./employee/position/position.component').then((m) => m.PositionComponent),
    }
    ]
  }
];


@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild(admin),
    CommonComponent,
  ],
  exports: [RouterModule],
})
export class CommonManageModule {
  static routes = admin;
}
