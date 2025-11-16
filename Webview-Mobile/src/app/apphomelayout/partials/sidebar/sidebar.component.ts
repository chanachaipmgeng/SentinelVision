import { AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit, SimpleChanges } from '@angular/core';
import { CompanyModel } from 'src/app/shared/models/company.model';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { ConfigService } from 'src/app/shared/services/config.service';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { NativeMobileService } from 'src/app/shared/services/native-mobile.service';
import { TokenService } from 'src/app/shared/services/token.service';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss']
})
export class SidebarComponent implements OnInit {
  companyModel: CompanyModel
  employeeModel?: EmployeeModel
  listMenu: {
    link: string
    icon: string
    name: string
    url?: string
  }[] = []

  lang = localStorage.getItem("Lang") ? localStorage.getItem("Lang") : "th"
  constructor(private employeeService: EmployeeService,
    public tokenService: TokenService,
    private configService: ConfigService,
    private cdr: ChangeDetectorRef,
    private nativeMobileService: NativeMobileService) {
    this.companyModel = this.tokenService.getSelectCompany()
    this.getDataEmp()
  }

  ngDoCheck(): void {
    if (this.tokenService.getSelectCompany().companyId != this.companyModel.companyId ||
      window.localStorage.getItem("reset-sidebar") == "true") {
      window.localStorage.removeItem("reset-sidebar")
      this.companyModel = this.tokenService.getSelectCompany()
      this.getDataEmp()
      this.cdr.markForCheck()
    }
  }

  ngOnInit() {

  }

  public getDataEmp() {
    this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.tokenService.getUser().member.memberId).subscribe(result => {
      this.employeeModel = result

      this.listMenu = [
        {
          link: "/company/personal-info/" + this.employeeModel.member.memberId,
          icon: "../assets/img/icon-menu/personal-info.png",
          name: "Personal Info"
        },
        {
          link: "/company/timestamp-log/" + this.employeeModel.member.memberId,
          icon: "../assets/img/icon-menu/timestamp-log.png",
          name: "Timestamp"
        },
        {
          link: "/company/company-menu",
          icon: "../assets/img/icon-menu/company-menu.png",
          name: "Company Info"
        }
      ]
      this.getSub()
      if (this.employeeModel.companyRoleType==1) {
        this.listMenu.push({
          link: "/company/human-resources-menu",
          icon: "../assets/img/icon-menu/ฝ่ายบุคคล.png",
          name: "HR"
        })
      }
    })
  }

  getSub() {
    this.employeeService.getSubordinateList(this.tokenService.getSelectCompany().companyId, this.tokenService.getUser().member.memberId).subscribe(result => {
      if (result.length > 0) {
        this.listMenu.push({
          link: "/company/subordinate-menu",
          icon: "../assets/img/icon-menu/subordinate-menu.png",
          name: "Subordinate Data"
        })
      }
    })
  }

  menuclose() {
    const body = document.getElementsByTagName('body')[0];
    body.classList.remove('menu-open');
  }

  logout() {
    this.tokenService.signOut();
  }
}
