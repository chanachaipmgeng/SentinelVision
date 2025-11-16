import { Component, OnInit } from '@angular/core';
import { TokenService } from '../shared/services/token.service';
import { TranslateService } from '@ngx-translate/core';
import { NativeMobileService } from '../shared/services/native-mobile.service';
import { EmployeeService } from '../shared/services/employee.service';
import { EmployeeModel } from '../shared/models/employee.model';
import { UserProfileModel } from '../shared/models/user.model';

@Component({
  selector: 'app-general-setting',
  templateUrl: './general-setting.component.html',
  styleUrls: ['./general-setting.component.css']
})
export class GeneralSettingComponent implements OnInit {
  selectedLanguage = 'th'
  versionApp = ""
  memberModel: UserProfileModel = new UserProfileModel()

  delayTime = ''
  delaySetting = false
  distance = '1'
  distanceNum = [40, 35, 30, 25, 20, 15, 10, 5]
  distanceSetting = false
  constructor(
    private memberService: EmployeeService,
    private tokenService: TokenService,
    public translate: TranslateService,
    private mobileService: NativeMobileService) {
    this.memberModel = new UserProfileModel(this.tokenService.getUser().member, this.translate)
  }

  ngOnInit() {
    this.translate.use(localStorage.getItem("Lang") != null
      ? localStorage.getItem("Lang")!
      : "th"
    );
    this.selectedLanguage = localStorage.getItem("Lang") != null
      ? localStorage.getItem("Lang")!
      : "th";
  }

  logout() {
    this.tokenService.signOut()
  }

  changeLanguage(lang: any) {
    localStorage.setItem("Lang", lang);
    this.translate.use(lang);
    this.selectedLanguage = lang;
    this.mobileService.changeLanguage(lang)
  }

  enrollment() {
    this.mobileService.goEnrollment(this.tokenService.getSelectCompany().companyId, this.tokenService.getUser().member.memberId)
  }

  // getVersion() {
  //   this.versionApp = this.mobileService.getVersionApp()
  // }


  soundSetting() {
    this.mobileService.setTimestampSound()
  }

  setTimestampDisplayDelay() {
    this.mobileService.setTimestampDisplayDelay(parseInt(this.delayTime))
  }

  setCameraDistance() {
    this.mobileService.setCameraDistance(this.distanceNum[parseInt(this.distance) - 1])
  }
}
