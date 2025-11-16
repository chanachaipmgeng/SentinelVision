import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { Subscription } from 'rxjs';
import { CompanyModel } from 'src/app/shared/models/company.model';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { CompanyService } from 'src/app/shared/services/company.service';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-company-menu',
  templateUrl: './company-menu.component.html',
  styleUrls: ['./company-menu.component.scss']
})
export class CompanyMenuComponent implements OnInit {
  markers: {
    latitude: number,
    longitude: number,
  }[] = []
  employee: EmployeeModel = new EmployeeModel()
  employeeServiceSub?: Subscription
  remark = ""
  date = new Date()
  memberIdParam: string | null
  companyModel: CompanyModel
  constructor(private tokenService: TokenService,
    private employeeService: EmployeeService,
    private modalService: NgbModal,
    private route: ActivatedRoute,
    private companyService: CompanyService,
  ) {
    this.memberIdParam = this.route.snapshot.paramMap.get('memberId')
  }
  ngOnInit() {
    this.companyService.getById(this.tokenService.getSelectCompany().companyId).subscribe(result => {
      this.companyModel = result
    })
  }
  checkText(text?: any) {
    return text ? text : '-'
  }
}
