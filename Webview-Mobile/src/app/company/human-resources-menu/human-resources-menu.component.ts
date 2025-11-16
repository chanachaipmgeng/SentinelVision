import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { Subscription } from 'rxjs';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-human-resources-menu',
  templateUrl: './human-resources-menu.component.html',
  styleUrls: ['./human-resources-menu.component.css']
})
export class HumanResourcesMenuComponent implements OnInit {

  employee: EmployeeModel = new EmployeeModel()
  employeeServiceSub?: Subscription
  remark = ""
  date = new Date()
  memberIdParam: string | null
  constructor(private tokenService: TokenService,
    private employeeService: EmployeeService,
    private modalService: NgbModal,
    private route: ActivatedRoute
  ) {
    this.memberIdParam = this.route.snapshot.paramMap.get('memberId')
  }
  ngOnInit() {
    this.employeeServiceSub?.unsubscribe()
    this.employeeServiceSub = this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.tokenService.getUser().member.memberId).subscribe(result => {
      this.employee = result
    })
  }
  checkText(text?: any) {
    return text ? text : '-'
  }
}
