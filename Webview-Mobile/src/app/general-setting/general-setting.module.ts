import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { GeneralSettingComponent } from './general-setting.component';
import { RouterModule, Routes } from '@angular/router';
import { EnrollmentFaceSettingComponent } from './facescan-setting/enrollment-face-setting/enrollment-face-setting.component';
import { ResetSettingComponent } from './facescan-setting/reset-setting/reset-setting.component';
import { ProfileInfoEditComponent } from './profile-info-edit/profile-info-edit.component';
import { ResetPasswordComponent } from './reset-password/reset-password.component';
import { ListOfDevicesComponent } from './list-of-devices/list-of-devices.component';
import { PersonAccessingComponent } from './person-accessing/person-accessing.component';
import { ContactUsComponent } from './contact-us/contact-us.component';
const routes: Routes = [
  {
    path: '',
    children: [
      {
        path: '',
        component: GeneralSettingComponent,
        data: {
          title: 'General Settings'
        },
      },
      {
        path: 'enroll-face',
        component: EnrollmentFaceSettingComponent,
        data: {
          title: 'Enrollment Setiing'
        },
      },
      {
        path: 'reset-setting',
        component: ResetSettingComponent,
        data: {
          title: 'Reset Settings',
          isBack : true,
        },
      },
      {
        path: 'profile-info-edit',
        component: ProfileInfoEditComponent,
        data: {
          title: 'Profile Info Edit',
          isBack : true,
        },
      },
      {
        path: 'reset-password',
        component: ResetPasswordComponent,
        data: {
          title: 'reset password',
          isBack : true,
        },
      },
      {
        path: 'list-of-devices',
        component: ListOfDevicesComponent,
        data: {
          title: 'Device Access',
          isBack : true,
        },
      },
      {
        path: 'person-accessing',
        component: PersonAccessingComponent,
        data: {
          title: 'Person Access',
          isBack : true,
        },
      },
      {
        path: 'contact-us',
        component: ContactUsComponent,
        data: {
          title: 'Contact us',
          isBack : true,
        },
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
export class GeneralSettingModule { }
