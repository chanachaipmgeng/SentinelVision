import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-profile-menu',
  templateUrl: './profile-menu.component.html',
  styleUrls: ['./profile-menu.component.scss']
})
export class ProfileMenuComponent {
  employeeServiceSub?: Subscription
  employee: EmployeeModel
  pictureUrl = ""
  fullName = ""
  companyName = ""
  constructor(private routes: Router,
    private tokenService: TokenService,
    private employeeService: EmployeeService
  ) { }

  ngOnInit() {
    this.employeeServiceSub?.unsubscribe()
    this.employeeServiceSub = this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.tokenService.getUser().member.memberId).subscribe(result => {
      this.employee = result
      this.companyName = this.tokenService.getSelectCompany().companyName
    })
  }

  routerLink(path: string) {
    this.routes.navigate([path]);
  }
}
