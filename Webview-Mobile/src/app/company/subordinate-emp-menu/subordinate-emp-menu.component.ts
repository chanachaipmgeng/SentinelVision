import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { Subscription } from 'rxjs';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { NativeMobileService } from 'src/app/shared/services/native-mobile.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-subordinate-emp-menu',
  templateUrl: './subordinate-emp-menu.component.html',
  styleUrls: ['./subordinate-emp-menu.component.scss']
})
export class SubordinateEmpMenuComponent {
  employee: EmployeeModel = new EmployeeModel()
  employeeServiceSub?: Subscription
  remark = ""
  date = new Date()
  memberIdParam: string = ""
  constructor(private tokenService: TokenService,
    private employeeService: EmployeeService,
    private modalService: NgbModal,
    private route: ActivatedRoute,
    private mobileService: NativeMobileService
  ) {
    this.memberIdParam = this.route.snapshot.paramMap.get('memberId')!
    if (this.memberIdParam) {
      this.employeeServiceSub?.unsubscribe()
      this.employeeServiceSub = this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.memberIdParam).subscribe(result => {
        this.employee = result
      })
    }
  }
  ngOnInit() {

  }
  checkText(text?: any) {
    return text ? text : '-'
  }

  enrollment(){
    this.mobileService.goEnrollment(this.tokenService.getSelectCompany().companyId, this.memberIdParam)
  }

  goTimestamp() {
    this.mobileService.goTimestamp(this.tokenService.getSelectCompany().companyId, this.memberIdParam)
  }
}
