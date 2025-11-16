import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { CompanyModel } from 'src/app/shared/models/company.model';
import { CompanyService } from 'src/app/shared/services/company.service';
import { ConfigService } from 'src/app/shared/services/config.service';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-company-list',
  templateUrl: './company-list.component.html',
  styleUrls: ['./company-list.component.scss']
})
export class CompanyListComponent implements OnInit {
  companyList: CompanyModel[] = []

  search = ""
  constructor(public tokenService: TokenService, private router: Router,
    private configService: ConfigService,
    private companyService: CompanyService,
    private empService: EmployeeService
  ) { }

  ngOnInit() {
    this.getCompanyList()
  }

  getCompanyList() {
    this.empService.getCompanyEmp(this.tokenService.getUser().member.memberId).subscribe(result => {
      this.companyList = result
    })
  }


  selectCompany(item: CompanyModel) {
    window.localStorage.setItem("reset-sidebar", "true");
    this.tokenService.saveSelectCompany(item)
    this.router.navigate(["/company/home-company"]);
  }

  filterCompany(item: CompanyModel[]) {
    return item.filter(x => x.companyName.toLowerCase().indexOf(this.search.toLowerCase()) != -1)
  }
}
