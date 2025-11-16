import { Component, OnInit } from '@angular/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { EmployeeHrModel } from 'src/app/shared/models/employeeHr.model';
import { CompanyService } from 'src/app/shared/services/company.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-hr-user-management',
  templateUrl: './hr-user-management.component.html',
  styleUrls: ['./hr-user-management.component.scss']
})
export class HrUserManagementComponent implements OnInit {
  employeeList: EmployeeHrModel[] = []
  search = ""
  constructor(private companyService: CompanyService,
    private modalService: NgbModal,
    private tokenService: TokenService) {

  }
  ngOnInit(): void {
    this.getCompanyHrList()
  }

  employeeFilter(): EmployeeHrModel[] {
    return this.employeeList.filter(x => (x.firstName + " " + x.lastName)?.toLowerCase().indexOf(this.search.trim().toLowerCase()) != -1)
  }

  getCompanyHrList() {
    // this.companyService.getCompanyHrList(this.tokenService.getSelectCompany().companyId).subscribe(response => {
    //   this.employeeList = response
    // })
  }

  deleteHr(employee: EmployeeHrModel) {
    // const modalRef = this.modalService.open(AlertComponent, { centered: true })
    // modalRef.componentInstance.headModal = "Add Hr"
    // modalRef.componentInstance.message = "Do you want to confirm?"
    // modalRef.componentInstance.confirmModal = true
    // modalRef.result.then(respone => {
    //   this.companyService.deleteCompanyHr(this.tokenService.getSelectCompany().companyId, employee.memberId).subscribe(response => {
    //     this.getCompanyHrList()
    //     const modalRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalRef.componentInstance.message = "STATUS.Success"
    //   }, error => {
    //     const modalRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalRef.componentInstance.message = "STATUS.Fail"
    //   })
    // }, error => {
    // })
  }
}
