import { Component, Input, OnInit } from '@angular/core';
import { CompanyModel } from 'src/app/shared/models/company.model';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';

import SwiperCore, {
  Navigation,
  Pagination,
  Scrollbar,
  A11y,
} from 'swiper/core';
SwiperCore.use([Navigation, Pagination, Scrollbar, A11y]);

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})

export class HomeComponent implements OnInit {
  isChecked: boolean = false;
  employeeModel?: EmployeeModel
  companyModel?: CompanyModel

  currentDate = new Date()
  constructor(private employeeService: EmployeeService, private tokenService: TokenService) { }
  ngOnInit(): void {
    this.getDataEmp()
    this.companyModel = this.tokenService.getSelectCompany()
  }

  getDataEmp() {
    this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.tokenService.getUser().member.memberId).subscribe(result => {
      this.employeeModel = result
      console.log(this.employeeModel)
    })
  }

  ngAfterInit(){


  }
  doCheck() {
    let html = document.getElementsByTagName('html')[0];
    this.isChecked = !this.isChecked;
    if (this.isChecked == true) {
      html.classList.add('dark-mode');
    } else {
      html.classList.remove('dark-mode');
    }
  }

}
