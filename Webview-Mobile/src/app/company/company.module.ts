import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import { CompanyListComponent } from './company-list/company-list.component';
import { PersonalInfoComponent } from './personal-info/personal-info.component';
import { WorkingPlanComponent } from './working-plan/working-plan.component';
import { DocReferComponent } from './doc-refer/doc-refer.component';
import { CompanyProfileComponent } from './company-profile/company-profile.component';
import { SubordinateDataComponent } from './subordinate-data/subordinate-data.component';
import { HomeCompanyComponent } from './home-company/home-company.component';
import { EmployeeListComponent } from './employee-list/employee-list.component';
import { PositionComponent } from './position/position.component';
import { ApprovalComponent } from './approval/approval.component';
import { TimestampLogComponent } from './timestamp-log/timestamp-log.component';
import { SubordinateWarningComponent } from './subordinate-warning/subordinate-warning.component';
import { ChangeBossComponent } from './change-boss/change-boss.component';
import { SubordinateMenuComponent } from './subordinate-menu/subordinate-menu.component';
import { DepartmentComponent } from './department/department.component';
import { CompanyMenuComponent } from './company-menu/company-menu.component';
import { HumanResourcesMenuComponent } from './human-resources-menu/human-resources-menu.component';
import { SubordinateEmpMenuComponent } from './subordinate-emp-menu/subordinate-emp-menu.component';
import { EmpApplyComponent } from './emp-apply/emp-apply.component';
import { SubordinateTimestampComponent } from './subordinate-timestamp/subordinate-timestamp.component';
import { HrUserManagementComponent } from './hr-user-management/hr-user-management.component';
import { HrUserManagementAddComponent } from './hr-user-management/hr-user-management-add/hr-user-management-add.component';
import { HrUserManagementEditComponent } from './hr-user-management/hr-user-management-edit/hr-user-management-edit.component';
import { SubordinateWarningTimestampComponent } from './subordinate-warning-timestamp/subordinate-warning-timestamp.component';
import { FeedNewsComponent } from './feed-news/feed-news.component';
import { EDocumentComponent } from './e-document/e-document.component';
import { SubWarningTimestampMapComponent } from './sub-warning-timestamp-map/sub-warning-timestamp-map.component';
import { NewsEventDetailComponent } from './news-event-detail/news-event-detail.component';
import { CompanyProfileMyhrComponent } from './company-profile-myhr/company-profile-myhr.component';
import { TimeManagenentMenuComponent } from './time-managenent-menu/time-managenent-menu.component';
import { EmpWarningTimeComponent } from './emp-warning-time/emp-warning-time.component';
import { EmployeeCreateComponent } from './employee-create/employee-create.component';
import { FaceScanComponent } from './face-scan/face-scan.component';
import { CompanyTimestampComponent } from './company-timestamp/company-timestamp.component';
const routes: Routes = [
  {
    path: '',
    // component: AppinnerlayoutComponent,

    children: [
      {
        path: 'home-company',
        component: HomeCompanyComponent,
        data: {
          title: 'Home'
        },
      },
      {
        path: 'home-company/:pin',
        component: HomeCompanyComponent,
        data: {
          title: 'Home'
        },
      },
      {
        path: 'feed-news',
        component: FeedNewsComponent,
        data: {
          title: 'Feed'
        },
      },
      {
        path: 'company-list',
        component: CompanyListComponent,
        data: {
          title: 'Company List'
        },
      },
      {
        path: 'timestamp-log/:memberId',
        component: TimestampLogComponent,
        data: {
          title: 'Timestamp',
          // isBack: true
        },
      },
      {
        path: 'personal-info/:memberId',
        component: PersonalInfoComponent,
        data: {
          title: 'Personal Info',
          // isBack: true
        },
      },
      {
        path: 'e-document',
        component: EDocumentComponent,
        data: {
          title: 'E-Document',
        },
      },
      { //ยังไม่ใช้
        path: 'working-plan',
        component: WorkingPlanComponent,
        data: {
          title: 'Working Plan'
        },
      },
      { //ยังไม่ใช้
        path: 'doc-refer',
        component: DocReferComponent,
        data: {
          title: 'Doc Refer'
        },
      },
      {
        path: 'time-management',
        component: TimeManagenentMenuComponent,
        data: {
          title: 'Work Infomation'
        },
      },
      { //เมนูแรกข้อมูลทีมงาน
        path: 'subordinate-menu',
        component: SubordinateMenuComponent,
        data: {
          title: 'Subordinate Data'
        },
      },
      {
        path: 'employee-menu/:memberId',
        component: SubordinateEmpMenuComponent,
        data: {
          title: 'Employee Information',
          isBack: true
        },
      },
      {
        path: 'subordinate-warning',
        component: SubordinateWarningComponent,
        data: {
          title: 'Emp Warning',
          isBack: true,
        },
      },
      {
        path: 'company-profile',
        component: CompanyProfileComponent,
        data: {
          title: 'Company Profile',
          isBack: true,
        },
      },
      {
        path: 'company-profile-myhr',
        component: CompanyProfileMyhrComponent,
        data: {
          title: 'Company Profile',
          isBack: true,
        },
      },
      {
        path: 'subordinate-data',
        component: SubordinateDataComponent,
        data: {
          title: 'Subordinate List',
          isBack: true
        },
      },
      {
        path: 'employee-list',
        component: EmployeeListComponent,
        data: {
          title: 'Employee List',
          isBack: true,
        },
      },
      {
        path: 'employee-create',
        component: EmployeeCreateComponent,
        data: {
          title: 'Employee Create',
          isBack: true,
        },
      },
      {
        path: 'emp-apply',
        component: EmpApplyComponent,
        data: {
          title: 'Apply Employee',
          isBack: true,
        },
      },
      {
        path: 'position',
        component: PositionComponent,
        data: {
          title: 'Position',
          isBack: true,
        },
      },
      {
        path: 'approval',
        component: ApprovalComponent,
        data: {
          title: 'การอนุมัติ'
        },
      },
      {
        path: 'change-boss/:memberId',
        component: ChangeBossComponent,
        data: {
          title: 'Change Boss',
          isBack: true,
        },
      },
      {
        path: 'company-menu',
        component: CompanyMenuComponent,
        data: {
          title: 'Company Info'
        },
      },
      {
        path: 'human-resources-menu',
        component: HumanResourcesMenuComponent,
        data: {
          title: 'HR'
        },
      },
      {
        path: 'department',
        component: DepartmentComponent,
        data: {
          title: 'Department',
          isBack: true,
        },
      },
      {
        path: 'subordinate-timestamp',
        component: SubordinateTimestampComponent,
        data: {
          title: 'Timestamp',
          isBack: true
        },
      },
      {
        path: 'company-timestamp',
        component: CompanyTimestampComponent,
        data: {
          title: 'Timestamp',
          isBack: true
        },
      },
      {
        path: 'hr-user-management',
        component: HrUserManagementComponent,
        data: {
          title: 'HR',
          isBack: true
        },
      },
      {
        path: 'hr-user-management-add',
        component: HrUserManagementAddComponent,
        data: {
          title: 'HR Management',
          isBack: true
        },
      },
      // {
      //   path: 'hr-user-management-edit/:memberId',
      //   component: HrUserManagementEditComponent,
      //   data: {
      //     title: 'Edit Hr User Management',
      //     isBack: true
      //   },
      // }
      {
        path: 'subordinate-warning-timestamp/:memberId',
        component: SubordinateWarningTimestampComponent,
        data: {
          title: 'List of Wrong Location Timestamp',
          isBack: true
        },
      },
      {
        path: 'sub-warning-timestamp-map',
        component: SubWarningTimestampMapComponent,
        data: {
          title: 'List of Wrong Location Timestamp',
          isBack: true
        },
      },
      {
        path: 'news-event-detail',
        component: NewsEventDetailComponent,
        data: {
          title: 'Detail',
          isBack: true,
        },
      },



      {
        path: 'employees-warning-time',
        component: EmpWarningTimeComponent,
        data: {
          title: 'Wrong Location Timestamp Approval',
          isBack: true,
        },
      },
      {
        path: 'face-scan',
        component: FaceScanComponent,
      },
    ]
  }
];
@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild(routes),
  ],
  exports: [RouterModule],
  declarations: []
})
export class CompanyModule { }
