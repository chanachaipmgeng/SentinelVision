import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-subordinate-data',
  templateUrl: './subordinate-data.component.html',
  styleUrls: ['./subordinate-data.component.scss']
})
export class SubordinateDataComponent {
  employeeServiceSub?: Subscription
  subordinateList: EmployeeModel[] = []
  search = ""
  constructor(private routes: Router,
    private employeeService: EmployeeService,
    private tokenService: TokenService) { }

  ngOnInit() {
    this.employeeServiceSub?.unsubscribe()
    this.employeeServiceSub = this.employeeService.getSubordinateList(this.tokenService.getSelectCompany().companyId, this.tokenService.getUser().member.memberId).subscribe(result => {
      this.subordinateList = result
    })
  }
  ngOnDestroy(): void {
    this.employeeServiceSub?.unsubscribe()

  }
  routerLink(path: string) {
    this.routes.navigate([path]);
  }

  subordinateListFilter(data: EmployeeModel[]): EmployeeModel[] {
    // return data.filter(x => x.getFullname().toLowerCase().indexOf(this.search.toLowerCase()) != -1)

    return data?.filter(
      (x) =>
        x.getFullname()?.toLowerCase().indexOf(this.search.toLowerCase()) !== -1 ||
        x.position.getName()?.toLowerCase().indexOf(this.search.toLowerCase()) !== -1 ||
        x.department.getName().toLowerCase().indexOf(this.search.toLowerCase()) !== -1 ||
        x.employeeId.toLowerCase().indexOf(this.search.toLowerCase()) !== -1
    );
  }
}
