import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { Subscription } from 'rxjs';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-change-boss',
  templateUrl: './change-boss.component.html',
  styleUrls: ['./change-boss.component.scss']
})
export class ChangeBossComponent {
  employeeList: EmployeeModel[] = []
  memberIdParam: string | null
  employeeServiceSub?: Subscription
  employee: EmployeeModel = new EmployeeModel()
  boss = ""
  bossEmp: EmployeeModel = new EmployeeModel()
  constructor(private employeeService: EmployeeService,
    private tokenService: TokenService,
    private route: ActivatedRoute,
    private modalService: NgbModal
  ) {
    this.memberIdParam = this.route.snapshot.paramMap.get('memberId')
    if (this.memberIdParam) {
      this.employeeServiceSub?.unsubscribe()
      this.employeeServiceSub = this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.memberIdParam).subscribe(result => {
        this.employee = result

      })
    }
    this.employeeService.getLists(this.tokenService.getSelectCompany().companyId).subscribe(response => {
      this.employeeList = response
    })
  }

  selectBoss() {
    this.bossEmp = this.employeeList.find(x => x.company_employeeId == this.boss) ? this.employeeList.find(x => x.company_employeeId == this.boss)! : new EmployeeModel()
  }

  ngOnDestroy(): void {
    this.employeeServiceSub?.unsubscribe()
  }

  checkText(text?: any) {
    return text ? text : '-'
  }

  submit() {
    // const modalRef = this.modalService.open(AlertComponent, { centered: true })
    // modalRef.componentInstance.message = "Do you want to confirm?"
    // modalRef.componentInstance.confirmModal = true
    // modalRef.result.then(respone => {
    //   const body = {
    //     memberId: this.employee.memberId!,
    //     companyId: this.employee.companyId!,
    //     employeeCode: this.employee.employeeCode!,
    //     bossMemberId: this.boss
    //   }
    //   this.employeeService.changeBoss(body).subscribe((response: any) => {
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
