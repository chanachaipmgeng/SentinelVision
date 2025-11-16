import { Component, OnInit } from '@angular/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslateService } from '@ngx-translate/core';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { DepartmentModel } from 'src/app/shared/models/department.model';
import { CompanyService } from 'src/app/shared/services/company.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-department',
  templateUrl: './department.component.html',
  styleUrls: ['./department.component.css']
})
export class DepartmentComponent implements OnInit {

  departmentModel: DepartmentModel[] = []
  search = ""
  departmentName=""
  headModal = ""

  constructor(
    private companyService: CompanyService,
    private tokenService: TokenService,
    private modalService: NgbModal,
    private translate: TranslateService
  ) { }

  ngOnInit() {
    this.getListdepartment();
  }

  getListdepartment(){
    // this.companyService.getListDepartment(this.tokenService.getSelectCompany().companyId).subscribe( result => {
    //   this.departmentModel = result
    //   console.log("model",result)
    // })
  }

  departmentListFilter(data: DepartmentModel[]): DepartmentModel[] {
    return data.filter(x => x.getName()?.toLowerCase().indexOf(this.search.toLowerCase()) != -1)
  }

  addDepartmentOpen(content: any, department?: DepartmentModel){
    // this.headModal = department ? "Edit Department" : "Add Department"
    // this.departmentName = department ? department.commonName : ""
    // const modalRef = this.modalService.open(content, { centered: true })
    // modalRef.result.then((result) => {
    //   if (department) {
    //     const body = {
    //       companyId: this.tokenService.getSelectCompany().companyId,
    //       commonId: department.commonId,
    //       commonName: this.departmentName,
    //       commonType: department.commonType
    //   }
    //   this.companyService.editDepartment(body).subscribe((response: any) => {
    //     this.getListdepartment();
    //     const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalAlertRef.componentInstance.message = "STATUS.Success"
    //   }, error => {
    //     const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalAlertRef.componentInstance.message = "STATUS.Fail"
    //   })}
    //   else {
    //     const body = {
    //       companyId: this.tokenService.getSelectCompany().companyId,
    //       commonName: this.departmentName,
    //       commonType: "Department"
    //     }
    //     this.companyService.createDepartment(body).subscribe((response: any) => {
    //       this.getListdepartment();
    //       const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
    //       modalAlertRef.componentInstance.message = "STATUS.Success"
    //     }, error => {
    //       const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
    //       modalAlertRef.componentInstance.message = "STATUS.Fail"
    //     })
    //   }
    // }, (reason) => {

    // });
  }

  deleteDepartment(department: DepartmentModel){
    // const modalRef = this.modalService.open(AlertComponent, { centered: true })
    // modalRef.componentInstance.headModal = "Delete Department"
    // modalRef.componentInstance.message = "Do you want to confirm?"
    // modalRef.componentInstance.confirmModal = true
    // modalRef.result.then(respone => {
    //   this.companyService.deleteDepartment(this.tokenService.getSelectCompany().companyId, department?.commonId).subscribe((response: any) => {
    //     this.getListdepartment();
    //     const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalAlertRef.componentInstance.message = "STATUS.Success"
    //   }, error => {
    //     const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
    //     modalAlertRef.componentInstance.message = "STATUS.Fail"
    //   })
    // })
  }


}
