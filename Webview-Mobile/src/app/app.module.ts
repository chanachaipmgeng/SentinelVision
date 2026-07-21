import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { SwiperModule } from 'swiper/angular';
import { NgCircleProgressModule } from 'ng-circle-progress';
import { Daterangepicker } from 'ng2-daterangepicker';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { AuthlayoutComponent } from './authlayout/authlayout.component';
import { ApphomelayoutComponent } from './apphomelayout/apphomelayout.component';
import { LandingComponent } from './authlayout/landing/landing.component';
import { SigninComponent } from './authlayout/signin/signin.component';
import { SignupComponent } from './authlayout/signup/signup.component';
import { ForgetpasswordComponent } from './authlayout/forgetpassword/forgetpassword.component';
import { ResetpasswordComponent } from './authlayout/resetpassword/resetpassword.component';
import { VerifyComponent } from './authlayout/verify/verify.component';
import { ThankyouComponent } from './authlayout/thankyou/thankyou.component';
import { StaticfooterComponent } from './apphomelayout/partials/staticfooter/staticfooter.component';
import { HeadermenuComponent } from './apphomelayout/partials/headermenu/headermenu.component';
import { SidebarComponent } from './apphomelayout/partials/sidebar/sidebar.component';
import { SplashComponent } from './authlayout/splash/splash.component';
import { Thankyou2Component } from './authlayout/thankyou2/thankyou2.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HTTP_INTERCEPTORS, HttpClient, HttpClientModule } from '@angular/common/http';
import { HttpRequestInterceptor } from './shared/http-request.interceptor';
import { DatePipe } from '@angular/common';
import { AgmCoreModule } from '@agm/core';
import { ThaiDatePipe } from './shared/pipes/thaidate.pipe';
import { ProfileInfoEditComponent } from './general-setting/profile-info-edit/profile-info-edit.component';
import { PersonalInfoComponent } from './company/personal-info/personal-info.component';
import { ProfileMenuComponent } from './company/profile-menu/profile-menu.component';
import { SubordinateDataComponent } from './company/subordinate-data/subordinate-data.component';
import { CompanyListComponent } from './company/company-list/company-list.component';
import { HomeCompanyComponent } from './company/home-company/home-company.component';
import { GeneralSettingComponent } from './general-setting/general-setting.component';
import { EnrollmentFaceSettingComponent } from './general-setting/facescan-setting/enrollment-face-setting/enrollment-face-setting.component';
import { AppsServiceOtherComponent } from './apps-service-other/apps-service-other.component';
import { DashboardCompanyComponent } from './company/dashboard-company/dashboard-company.component';
import { BarchartComponent } from './apphomelayout/stats/barchart/barchart.component';
import { DoughnutChartComponent } from './apphomelayout/stats/doughnut-chart/doughnut-chart.component';
import { SmallchartoneComponent } from './apphomelayout/stats/smallchartone/smallchartone.component';
import { SmallchartwoComponent } from './apphomelayout/stats/smallchartwo/smallchartwo.component';
import { SmallcharthreeComponent } from './apphomelayout/stats/smallcharthree/smallcharthree.component';
import { SmallcharfourComponent } from './apphomelayout/stats/smallcharfour/smallcharfour.component';
import { ChartsModule } from 'ng2-charts';
import { UseHttpImageSourcePipe } from './shared/pipe-http-img';
import { CompanyProfileComponent } from './company/company-profile/company-profile.component';
import { AlertComponent } from './shared/component/alert/alert.component';
import { ImageModule } from './image/image.module';
import { TimestampLogComponent } from './company/timestamp-log/timestamp-log.component';
import { EmployeeListComponent } from './company/employee-list/employee-list.component';
import { ResetPasswordComponent } from './general-setting/reset-password/reset-password.component';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { TranslateHttpLoader } from '@ngx-translate/http-loader';
import { PositionComponent } from './company/position/position.component';
import { SubordinateWarningComponent } from './company/subordinate-warning/subordinate-warning.component';
import { FileUploadModule } from 'ng2-file-upload';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';
import { ChangeBossComponent } from './company/change-boss/change-boss.component';
import { SubordinateMenuComponent } from './company/subordinate-menu/subordinate-menu.component';
import { SubordinateEmpMenuComponent } from './company/subordinate-emp-menu/subordinate-emp-menu.component';
import { DepartmentComponent } from './company/department/department.component';
import { CompanyMenuComponent } from './company/company-menu/company-menu.component';
import { HumanResourcesMenuComponent } from './company/human-resources-menu/human-resources-menu.component';
import { EmpApplyComponent } from './company/emp-apply/emp-apply.component';
import { SubordinateTimestampComponent } from './company/subordinate-timestamp/subordinate-timestamp.component';
import { HrUserManagementComponent } from './company/hr-user-management/hr-user-management.component';
import { HrUserManagementAddComponent } from './company/hr-user-management/hr-user-management-add/hr-user-management-add.component';
import { HrUserManagementEditComponent } from './company/hr-user-management/hr-user-management-edit/hr-user-management-edit.component';
import { SubordinateWarningTimestampComponent } from './company/subordinate-warning-timestamp/subordinate-warning-timestamp.component';
import { LOAD_WASM, NgxScannerQrcodeModule } from 'ngx-scanner-qrcode';
import { EDocumentComponent } from './company/e-document/e-document.component';
import { SubWarningTimestampMapComponent } from './company/sub-warning-timestamp-map/sub-warning-timestamp-map.component';
import { FullCalendarModule } from '@fullcalendar/angular';
import { ListOfDevicesComponent } from './general-setting/list-of-devices/list-of-devices.component';
import { PersonAccessingComponent } from './general-setting/person-accessing/person-accessing.component';
import { NewsEventDetailComponent } from './company/news-event-detail/news-event-detail.component';
import { TimeManagenentMenuComponent } from './company/time-managenent-menu/time-managenent-menu.component';
import { PdfViewerModule } from 'ng2-pdf-viewer';
import { EmpWarningTimeComponent } from './company/emp-warning-time/emp-warning-time.component';
import { ContactUsComponent } from './general-setting/contact-us/contact-us.component';
import { EmployeeCreateComponent } from './company/employee-create/employee-create.component';
import { PdpaComponent } from './company/pdpa/pdpa.component';
import { CompanyTimestampComponent } from './company/company-timestamp/company-timestamp.component';
import { FeedNewsComponent } from './company/feed-news/feed-news.component';
import { ApprovalComponent } from './company/approval/approval.component';
import { CompanyProfileMyhrComponent } from './company/company-profile-myhr/company-profile-myhr.component';
import { FaceScanComponent } from './company/face-scan/face-scan.component';
import { ResetSettingComponent } from './general-setting/facescan-setting/reset-setting/reset-setting.component';
import { DpuLocationMapComponent } from './shared/component/dpu-location-map/dpu-location-map.component';
import { environment } from '../environments/environment';

export function HttpLoaderFactory(http: HttpClient) {
  return new TranslateHttpLoader(http, './assets/i18n/', '.json');
}
LOAD_WASM().subscribe();

@NgModule({
  declarations: [
    AppComponent,
    AuthlayoutComponent,
    ApphomelayoutComponent,
    LandingComponent,
    SigninComponent,
    SignupComponent,
    ForgetpasswordComponent,
    ResetpasswordComponent,
    VerifyComponent,
    ThankyouComponent,
    StaticfooterComponent,
    HeadermenuComponent,
    SidebarComponent,
    SplashComponent,
    Thankyou2Component,
    CompanyListComponent,
    TimestampLogComponent,
    PersonalInfoComponent,
    ThaiDatePipe,
    SubordinateDataComponent,
    ProfileMenuComponent,
    ProfileInfoEditComponent,
    HomeCompanyComponent,
    GeneralSettingComponent,
    EnrollmentFaceSettingComponent,
    ResetSettingComponent,
    AppsServiceOtherComponent,
    DashboardCompanyComponent,
    BarchartComponent,
    DoughnutChartComponent,
    SmallchartoneComponent,
    SmallchartwoComponent,
    SmallcharthreeComponent,
    SmallcharfourComponent,
    UseHttpImageSourcePipe,
    CompanyProfileComponent,
    AlertComponent,
    EmployeeListComponent,
    ResetPasswordComponent,
    PositionComponent,
    SubordinateWarningComponent,
    ChangeBossComponent,
    SubordinateMenuComponent,
    SubordinateEmpMenuComponent,
    DepartmentComponent,
    CompanyMenuComponent,
    HumanResourcesMenuComponent,
    EmpApplyComponent,
    SubordinateTimestampComponent,
    CompanyTimestampComponent,
    HrUserManagementComponent,
    HrUserManagementAddComponent,
    HrUserManagementEditComponent,
    SubordinateWarningTimestampComponent,
    EDocumentComponent,
    SubWarningTimestampMapComponent,
    ListOfDevicesComponent,
    PersonAccessingComponent,
    NewsEventDetailComponent,
    TimeManagenentMenuComponent,
    EmpWarningTimeComponent,
    ContactUsComponent,
    EmployeeCreateComponent,
    PdpaComponent,
    FeedNewsComponent,
    ApprovalComponent,
    CompanyProfileMyhrComponent,
    DpuLocationMapComponent,
  ],
  imports: [
    PdfViewerModule,
    FileUploadModule,
    BrowserModule,
    BrowserAnimationsModule,
    AppRoutingModule,
    SwiperModule,
    ChartsModule,
    NgCircleProgressModule.forRoot(),
    Daterangepicker,
    FormsModule,
    ReactiveFormsModule,
    HttpClientModule,
    ImageModule,
    NgbModule,
    NgxScannerQrcodeModule,
    FullCalendarModule,
    FaceScanComponent,
    AgmCoreModule.forRoot({
      apiKey: environment.googleMapsApiKey,
      libraries: ['geometry', 'places'],
    }),
    TranslateModule.forRoot({
      loader: {
        provide: TranslateLoader,
        useFactory: HttpLoaderFactory,
        deps: [HttpClient],
      },
    }),
  ],
  providers: [
    DatePipe,
    {
      provide: HTTP_INTERCEPTORS,
      useClass: HttpRequestInterceptor,
      multi: true,
    },
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
