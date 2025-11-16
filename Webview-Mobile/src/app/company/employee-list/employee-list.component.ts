import { Component, OnInit } from '@angular/core';
import { map } from 'rxjs/operators';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-employee-list',
  templateUrl: './employee-list.component.html',
  styleUrls: ['./employee-list.component.css']
})
export class EmployeeListComponent implements OnInit {

  employeeList: EmployeeModel[] = []
  search = ""

  constructor(
    private employeeService: EmployeeService,
    private tokenService: TokenService
  ) { }

  ngOnInit() {
    this.getEmployee()
  }

  getEmployee() {
    this.employeeService.getLists(this.tokenService.getSelectCompany().companyId).subscribe(result => {
      this.employeeList = result
    })
  }

  empListFilter(data: EmployeeModel[]): EmployeeModel[] {
    return data?.filter(
      (x) =>
        x.getFullname()?.toLowerCase().indexOf(this.search.toLowerCase()) !== -1 ||
        x.position.getName()?.toLowerCase().indexOf(this.search.toLowerCase()) !== -1 ||
        x.department.getName().toLowerCase().indexOf(this.search.toLowerCase()) !== -1 ||
        x.employeeId.toLowerCase().indexOf(this.search.toLowerCase()) !== -1
    );
  }

}
