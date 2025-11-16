import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslateService } from '@ngx-translate/core';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { CompanyService } from 'src/app/shared/services/company.service';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-hr-user-management-add',
  templateUrl: './hr-user-management-add.component.html',
  styleUrls: ['./hr-user-management-add.component.scss']
})
export class HrUserManagementAddComponent {
  employee: EmployeeModel[] = []
  search = ""

  constructor(private employeeService: EmployeeService,
    private tokenService: TokenService,
    private companyService: CompanyService,
    private modalService: NgbModal,
    private router: Router) {
    this.employeeService.getLists(this.tokenService.getSelectCompany().companyId).subscribe(response => {
      this.employee = response
    })
  }

  employeeFilter(): EmployeeModel[] {
    return this.employee.filter(x => x.getFullname()?.toLowerCase().indexOf(this.search.trim().toLowerCase()) != -1)
  }

  addCompanyHr(employee: EmployeeModel) {
    // const modalRef = this.modalService.open(AlertComponent, { centered: true })
    // modalRef.componentInstance.headModal = "Add Hr User Management"
    // modalRef.componentInstance.message = "Do you want to confirm?"
    // modalRef.componentInstance.confirmModal = true
    // modalRef.result.then(respone => {
    //   const body = {
    //     memberId: employee.memberId!,
    //     companyId: this.tokenService.getSelectCompany().companyId,
    //     addingBy: this.tokenService.getUser().member.memberId
    //   }
    //   this.companyService.addCompanyHr(body).subscribe(response => {
    //     const modalRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalRef.componentInstance.message = "STATUS.Success"
    //     this.router.navigate(['/company/hr-user-management']);
    //   }, error => {
    //     const modalRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalRef.componentInstance.message = "STATUS.Fail"
    //   })
    // }, error => {
    // })
  }
}
