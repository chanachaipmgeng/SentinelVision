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
    // Legacy kiosk path — kept as alias; Phase 3 owns stationMode chrome on enroll-face.
    {
      path: 'company/timestamp-face',
      loadComponent: () =>
        import('./enroll-face/enroll-face.component').then((m) => m.EnrollFaceComponent),
    },
    {
      path: 'company/scan/:stationMode',
      loadComponent: () =>
        import('./enroll-face/enroll-face.component').then((m) => m.EnrollFaceComponent),
    },
    {
      path: 'company/scan-hub',
      loadComponent: () =>
        import('./scan-hub/scan-hub.component').then((m) => m.ScanHubComponent),
    },
    {
      path: 'company/warning-timestamp-log',
      loadComponent: () =>
        import('./warning-timetamp/warning-timetamp.component').then((m) => m.WarningTimetampComponent),
    },
    {
      path: 'company/approval-inbox',
      loadComponent: () =>
        import('./approval-inbox/approval-inbox.component').then((m) => m.ApprovalInboxComponent),
    },
    {
      path: 'company/reports',
      loadComponent: () =>
        import('./reports/reports.component').then((m) => m.ReportsComponent),
    },
    {
      path: 'company/self-service',
      loadComponent: () =>
        import('./self-service/self-service.component').then((m) => m.SelfServiceComponent),
    },
    {
      path: 'company/profile-security',
      loadComponent: () =>
        import('./profile-security/profile-security.component').then(
          (m) => m.ProfileSecurityComponent
        ),
    },
    {
      path: 'company/hr-schedule',
      loadComponent: () =>
        import('./hr-schedule/hr-schedule.component').then((m) => m.HrScheduleComponent),
    },
    // Param-driven thin views over sentinel-center (module workspaces).
    {
      path: 'company/access-control/:section',
      loadComponent: () =>
        import('./sentinel-center/sentinel-center.component').then(
          (m) => m.SentinelCenterComponent
        ),
      data: { moduleWorkspace: 'ACCESS_CONTROL' },
    },
    {
      path: 'company/watchlist/:section',
      loadComponent: () =>
        import('./sentinel-center/sentinel-center.component').then(
          (m) => m.SentinelCenterComponent
        ),
      data: { moduleWorkspace: 'WATCHLIST' },
    },
    {
      path: 'company/visitors/:section',
      loadComponent: () =>
        import('./sentinel-center/sentinel-center.component').then(
          (m) => m.SentinelCenterComponent
        ),
      data: { moduleWorkspace: 'VISITOR' },
    },
    {
      path: 'company/events/:section',
      loadComponent: () =>
        import('./sentinel-center/sentinel-center.component').then(
          (m) => m.SentinelCenterComponent
        ),
      data: { moduleWorkspace: 'EVENTS' },
    },
    // Legacy monolith; ?tab= redirects into module routes inside the component.
    {
      path: 'company/sentinel-center',
      loadComponent: () =>
        import('./sentinel-center/sentinel-center.component').then(
          (m) => m.SentinelCenterComponent
        ),
    },
    {
      path: 'company/audit-log',
      loadComponent: () =>
        import('./audit-log/audit-log.component').then((m) => m.AuditLogComponent),
    },
    {
      path: 'company/devices',
      loadComponent: () =>
        import('./devices/devices.component').then((m) => m.DevicesComponent),
    },
    {
      path: 'company/notification-center',
      loadComponent: () =>
        import('./notification-center/notification-center.component').then(
          (m) => m.NotificationCenterComponent
        ),
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
