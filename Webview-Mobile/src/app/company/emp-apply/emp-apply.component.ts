import { Component } from '@angular/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { DepartmentModel } from 'src/app/shared/models/department.model';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { PositionModel } from 'src/app/shared/models/position.model';
import { CompanyService } from 'src/app/shared/services/company.service';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-emp-apply',
  templateUrl: './emp-apply.component.html',
  styleUrls: ['./emp-apply.component.scss']
})
export class EmpApplyComponent {
  departmentList :DepartmentModel[] = []
  employeeList: EmployeeModel[] = []
  employeeBossList: EmployeeModel[] = []
  positionList: PositionModel[] = []
  search:string = ''

  modelApply = {
    employeeId: '',
    employeeName: '',
    memberId: '',
    companyId: '',
    branch: '',
    positionApplyForm: '',
    departmentApplyForm: '',
    bossMajorApplyForm: ''
  }
  constructor(
    private employeeService: EmployeeService,
    private companyService:CompanyService,
    private tokenService: TokenService,
    private modalService: NgbModal
  ) { }

  ngOnInit() {
    // this.getEmployeeApply();
    // this.getListBranch();
    // this.getListDepartment();
    // this.getListPosition();
    // this.getEmpListBoss();
  }
  filterListEmp(){
    return this.employeeList.filter(x => x.getFullname().toLowerCase().includes(this.search.toLowerCase()))
  }
  // getEmployeeApply() {
  //   this.companyService.getListApply(this.tokenService.getSelectCompany().companyId).subscribe(result => {
  //     this.employeeList = result
  //   })
  // }
  // getListBranch(){
  //   this.companyService.getListBranch(this.tokenService.getSelectCompany().companyId).subscribe(result => {
  //     this.branchList = result
  //   })
  // }
  // getListDepartment(){
  //   this.companyService.getListDepartment(this.tokenService.getSelectCompany().companyId).subscribe(result => {
  //     this.departmentList = result
  //   })
  // }
  // getListPosition(){
  //   this.companyService.getListPosition(this.tokenService.getSelectCompany().companyId).subscribe(result => {
  //     this.positionList = result
  //   })
  // }
  // getEmpListBoss(){
  //   this.employeeService.getEmpList(this.tokenService.getSelectCompany().companyId).subscribe(result => {
  //     this.employeeBossList = result
  //     console.log("🚀 ~ EmpApplyComponent ~ this.employeeService.getEmpList ~ this.employeeBossList:", this.employeeBossList)
  //   })
  // }
  openApply(content: any,item:EmployeeModel) {
    // this.modelApply = {
    //   employeeId: '',
    //   employeeName: item.memberName,
    //   memberId: item.memberId,
    //   companyId: item.companyId,
    //   branch: item.branchId,
    //   positionApplyForm: '',
    //   departmentApplyForm: '',
    //   bossMajorApplyForm: ''
    // }
    // const modalRef = this.modalService.open(content, { centered: true })

  }
  onSubmit(status:number) {
    const modalRef = this.modalService.open(AlertComponent, { centered: true })
    modalRef.componentInstance.message = "Do you want to confirm?"
    modalRef.componentInstance.confirmModal = true
    modalRef.result.then(respone => {
      this.modalService.dismissAll();
      const now = Date.now();
      const body = {
          companyId: this.modelApply.companyId,
          employeeCode: '',
          memberId: this.modelApply.memberId,
          applyDate: now,
          positionName: this.modelApply.positionApplyForm,
          departmentName: this.modelApply.departmentApplyForm,
          remark: "",
          approveStatus: status,
          bossMajorId: this.modelApply.bossMajorApplyForm,
          branchId: this.modelApply.branch,
          lagacyCode: this.modelApply.employeeId,
        };
      // this.companyService.submitApprovedEmployee(body).then((response: any) => {
      //   const modalRef = this.modalService.open(AlertComponent, { centered: true })
      //   modalRef.componentInstance.message = "STATUS.Success"
      //   this.getEmployeeApply();
      // }, error => {
      //   const modalRef = this.modalService.open(AlertComponent, { centered: true })
      //   modalRef.componentInstance.message = "STATUS.Fail"
      // })
    }, error => {
    })
  }
}
