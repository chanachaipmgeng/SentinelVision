import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstallManagementComponent } from './company-management.component';
import { RouterModule, Routes } from '@angular/router';

import { RoleGuard } from '../../shared/services/role.guard';

export const companyRoutes: Routes = [
  {
    path: '',
    canActivateChild: [RoleGuard],
    data: { area: 'company' },
    children: [
    {
      path: 'company/home/:companyId',
      loadComponent: () =>
        import('./home-installer/home-installer.component').then((m) => m.HomeInstallerComponent),
    },
    {
      path: 'company/dashboard',
      loadComponent: () =>
        import('./dashboard/dashboard.component').then((m) => m.DashboardComponent),
    },
    {
      path: 'company/company-info',
      loadComponent: () =>
        import('./company-info/company-info.component').then((m) => m.CompanyInfoComponent),
    },
    {
      path: 'company/company-location',
      loadComponent: () =>
        import('./company-location/company-location.component').then((m) => m.CompanyLocationComponent),
    },
    {
      path: 'company/company-department',
      loadComponent: () =>
        import('../common/employee/department/department.component').then((m) => m.DepartmentComponent),
    },
    {
      path: 'company/company-position',
      loadComponent: () =>
        import('../common/employee/position/position.component').then((m) => m.PositionComponent),
    },
    {
      path: 'company/company-emp',
      loadComponent: () =>
        import('./company-emp/company-emp.component').then((m) => m.CompanyEmpComponent),
    },
    {
      path: 'company/timestamp-log',
      loadComponent: () =>
        import('./timestamp-log/timestamp-log.component').then((m) => m.TimestampLogComponent),
    },
    {
      path: 'company/timestamp-log/:company_employeeId',
      loadComponent: () =>
        import('./timestamp-log/timestamp-log.component').then((m) => m.TimestampLogComponent),
    },
    {
      path: 'company/timestamp-face',
      loadComponent: () =>
        import('./enroll-face/enroll-face.component').then((m) => m.EnrollFaceComponent),
    },
    {
      path: 'company/warning-timestamp-log',
      loadComponent: () =>
        import('./warning-timetamp/warning-timetamp.component').then((m) => m.WarningTimetampComponent),
    },
    {
      path: 'company/hr-schedule',
      loadComponent: () =>
        import('./hr-schedule/hr-schedule.component').then((m) => m.HrScheduleComponent),
    },
    {
      path: 'company/audit-log',
      loadComponent: () =>
        import('./audit-log/audit-log.component').then((m) => m.AuditLogComponent),
    },
    ],
  },
];


@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild(companyRoutes)
  ],
  exports: [RouterModule],
  declarations: [InstallManagementComponent]
})
export class CompanyManagementModule {
  static routes = companyRoutes;
}
