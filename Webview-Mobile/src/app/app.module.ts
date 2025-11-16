import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { SwiperModule } from 'swiper/angular';
import { ChartsModule } from 'ng2-charts';
import { NgCircleProgressModule } from 'ng-circle-progress';
import { NouisliderModule } from 'ng2-nouislider';
// import { FullCalendarModule } from '@fullcalendar/angular'; // must go before plugins
// import dayGridPlugin from '@fullcalendar/daygrid'; // a plugin!
import { Daterangepicker } from 'ng2-daterangepicker';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { AuthlayoutComponent } from './authlayout/authlayout.component';
import { ApphomelayoutComponent } from './apphomelayout/apphomelayout.component';
import { AppinnerlayoutComponent } from './appinnerlayout/appinnerlayout.component';
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
import { HomeComponent } from './apphomelayout/home/home.component';
import { StatsComponent } from './apphomelayout/stats/stats.component';

import { BarchartComponent } from './apphomelayout/stats/barchart/barchart.component';
import { ProfileComponent } from './appinnerlayout/profile/profile.component';
import { StyleComponent } from './appinnerlayout/style/style.component';
import { FooterinfoComponent } from './appinnerlayout/partials/footerinfo/footerinfo.component';
import { HeaderbackComponent } from './appinnerlayout/partials/headerback/headerback.component';
import { ChatlistComponent } from './appinnerlayout/chatlist/chatlist.component';
import { MessagesComponent } from './appinnerlayout/messages/messages.component';
import { NotificationsComponent } from './appinnerlayout/notifications/notifications.component';
import { PagesComponent } from './appinnerlayout/pages/pages.component';
import { SettingsComponent } from './appinnerlayout/settings/settings.component';
import { FaqsComponent } from './appinnerlayout/faqs/faqs.component';
import { TimelineComponent } from './appinnerlayout/timeline/timeline.component';
import { UserlistComponent } from './appinnerlayout/userlist/userlist.component';
import { ContactusComponent } from './appinnerlayout/contactus/contactus.component';
import { PricingComponent } from './appinnerlayout/pricing/pricing.component';
import { TermsandcoditionComponent } from './appinnerlayout/termsandcodition/termsandcodition.component';
import { PagenotfoundComponent } from './appinnerlayout/pagenotfound/pagenotfound.component';
import { BlogComponent } from './appinnerlayout/blog/blog.component';
import { BlogdetailsComponent } from './appinnerlayout/blogdetails/blogdetails.component';
import { SplashComponent } from './authlayout/splash/splash.component';
import { Thankyou2Component } from './authlayout/thankyou2/thankyou2.component';
import { DoughnutChartComponent } from './apphomelayout/stats/doughnut-chart/doughnut-chart.component';
import { SmallchartoneComponent } from './apphomelayout/stats/smallchartone/smallchartone.component';
import { SmallchartwoComponent } from './apphomelayout/stats/smallchartwo/smallchartwo.component';
import { SmallcharthreeComponent } from './apphomelayout/stats/smallcharthree/smallcharthree.component';
import { SmallcharfourComponent } from './apphomelayout/stats/smallcharfour/smallcharfour.component';
import { PayComponent } from './apphomelayout/pay/pay.component';
import { SendmoneyComponent } from './apphomelayout/sendmoney/sendmoney.component';
import { ReceivemoneyComponent } from './apphomelayout/receivemoney/receivemoney.component';
import { BillsComponent } from './apphomelayout/bills/bills.component';
import { RewardsComponent } from './apphomelayout/rewards/rewards.component';
import { WalletComponent } from './apphomelayout/wallet/wallet.component';
import { DoughnutchartwalletComponent } from './apphomelayout/wallet/doughnutchartwallet/doughnutchartwallet.component';
import { Sendmoney1Component } from './appinnerlayout/sendmoney1/sendmoney1.component';
import { Sendmoney2Component } from './appinnerlayout/sendmoney2/sendmoney2.component';
import { Sendmoney3Component } from './appinnerlayout/sendmoney3/sendmoney3.component';
import { AllreceivemoneyComponent } from './appinnerlayout/allreceivemoney/allreceivemoney.component';
import { WithdrawComponent } from './appinnerlayout/withdraw/withdraw.component';
import { Thankyou3Component } from './appinnerlayout/thankyou3/thankyou3.component';
import { Thankyou4Component } from './appinnerlayout/thankyou4/thankyou4.component';
import { AddmoneyComponent } from './appinnerlayout/addmoney/addmoney.component';
import { AboutusComponent } from './appinnerlayout/aboutus/aboutus.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HTTP_INTERCEPTORS, HttpClient, HttpClientModule } from "@angular/common/http";
import { HttpRequestInterceptor } from "./shared/http-request.interceptor";
import { DatePipe } from '@angular/common';
import { AgmCoreModule } from '@agm/core';
import { ThaiDatePipe } from './appinnerlayout/thaidate.pipe';
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
// FullCalendarModule.registerPlugins([ // register FullCalendar plugins
//   dayGridPlugin
// ]);
export function HttpLoaderFactory(http: HttpClient) {
  return new TranslateHttpLoader(http, './assets/i18n/', '.json');
}
LOAD_WASM().subscribe();
@NgModule({
  declarations: [
    AppComponent,
    AuthlayoutComponent,
    ApphomelayoutComponent,
    AppinnerlayoutComponent,
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
    HomeComponent,
    StatsComponent,
    BarchartComponent,
    ProfileComponent,
    StyleComponent,
    FooterinfoComponent,
    HeaderbackComponent,
    ChatlistComponent,
    MessagesComponent,
    NotificationsComponent,
    PagesComponent,
    SettingsComponent,
    FaqsComponent,
    TimelineComponent,
    UserlistComponent,
    ContactusComponent,
    PricingComponent,
    TermsandcoditionComponent,
    PagenotfoundComponent,
    BlogComponent,
    BlogdetailsComponent,
    SplashComponent,
    Thankyou2Component,
    DoughnutChartComponent,
    SmallchartoneComponent,
    SmallchartwoComponent,
    SmallcharthreeComponent,
    SmallcharfourComponent,
    PayComponent,
    SendmoneyComponent,
    ReceivemoneyComponent,
    BillsComponent,
    RewardsComponent,
    WalletComponent,
    DoughnutchartwalletComponent,
    Sendmoney1Component,
    Sendmoney2Component,
    Sendmoney3Component,
    AllreceivemoneyComponent,
    WithdrawComponent,
    Thankyou3Component,
    Thankyou4Component,
    AddmoneyComponent,
    AboutusComponent,
    CompanyListComponent,
    TimestampLogComponent,
    PersonalInfoComponent,
    ThaiDatePipe,
    SubordinateDataComponent,
    PersonalInfoComponent,
    ProfileMenuComponent,
    ProfileInfoEditComponent,
    HomeCompanyComponent,
    GeneralSettingComponent,
    EnrollmentFaceSettingComponent,
    AppsServiceOtherComponent,
    CompanyListComponent,
    DashboardCompanyComponent,
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
    NouisliderModule,
    Daterangepicker,
    FormsModule,
    ReactiveFormsModule,
    HttpClientModule,
    ImageModule,
    NgbModule,
    NgxScannerQrcodeModule,
    FullCalendarModule,
    AgmCoreModule.forRoot({
      apiKey: '***REMOVED***',
      libraries: ['geometry', 'places'],
    }),
    TranslateModule.forRoot({
      loader: {
        provide: TranslateLoader,
        useFactory: HttpLoaderFactory,
        deps: [HttpClient]
      }
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
  exports: [
  ]
})
export class AppModule { }
