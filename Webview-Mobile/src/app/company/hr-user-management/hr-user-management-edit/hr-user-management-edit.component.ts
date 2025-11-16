import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { PermissionAccessService } from 'src/app/shared/services/permission-access.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-hr-user-management-edit',
  templateUrl: './hr-user-management-edit.component.html',
  styleUrls: ['./hr-user-management-edit.component.scss']
})
export class HrUserManagementEditComponent implements OnInit {
  employee: EmployeeModel = new EmployeeModel()
  memberId = ""

  zeepay = false;
  payslip = false;
  constructor(private route: ActivatedRoute,
    private employeeService: EmployeeService,
    private permissionAccessService: PermissionAccessService,
    private tokenService: TokenService) {
    this.memberId = this.route.snapshot.paramMap.get('memberId')!
    this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.memberId).subscribe(result => {
      this.employee = result
    })
    this.permissionAccessService.getlistHrConfig(this.tokenService.getSelectCompany().companyId, this.memberId).subscribe((result: any) => {
      if (result.length > 0) {
        this.zeepay = result[0].zeepay
        this.payslip = result[0].payslip
      }
    })
  }

  payslipChange() {
    let body = {
      companyId: this.tokenService.getSelectCompany().companyId,
      memberId: this.memberId,
      type: "PAYSLIP",
      status: this.payslip ? 1 : 0,
      editBy: this.tokenService.getUser().member.memberId,
      editName: ""
    }
    this.permissionAccessService.setConfig(body).subscribe(result => {
    });
  }

  zeepayChange() {
    let body = {
      companyId: this.tokenService.getSelectCompany().companyId,
      memberId: this.memberId,
      type: "ZEEPAY",
      status: this.zeepay ? 1 : 0,
      editBy: this.tokenService.getUser().member.memberId,
      editName: ""
    }
    this.permissionAccessService.setConfig(body).subscribe(result => {
    });
  }


  ngOnInit(): void {
  }
  checkText(text?: any) {
    return text ? text : '-'
  }

}
