import { DepartmentModel } from "./department.model";
import { BaseModel } from "./base.model";
import { TranslateService } from "@ngx-translate/core";
import { PositionModel } from "./position.model";
import { UserProfileModel } from "./user.model";
import { environment } from "../../../environments/environment";

export class EmployeeModel extends BaseModel{
  member: UserProfileModel;
  companyId: string;
  position: PositionModel;
  department: DepartmentModel;
  company_employeeId: string;
  employeeId: string;
  salary: number;
  bossId: string;
  companyRoleType: number;
  empType: number;
  startDate: string;
  constructor(
    data?: Partial<EmployeeModel>,
    translateService?: TranslateService
  ) {
    super(data, translateService);
    this.member = new UserProfileModel(data?.member, this.translateService)
    this.companyId = data?.companyId!
    this.position = new PositionModel(data?.position, this.translateService)
    this.department = new DepartmentModel(data?.department, this.translateService)
    this.employeeId = data?.employeeId!;
    this.company_employeeId = data?.company_employeeId!;
    this.bossId = data?.bossId!;
    this.startDate = data?.startDate!
    this.salary = data?.salary!
    this.empType = data?.empType!
    this.companyRoleType = data?.companyRoleType!
  }

  getFullname(): string {
    return this.member.firstName + " " + this.member.lastName
  }

  getPicture(): string {
    return this.member.picture ? environment.baseUrl + '/images/' + this.member.picture : './assets/images/faces/1.jpg'
  }

  getType(): string {
    if (this.empType == 1) {
      return this.translateService.instant('รายเดือน')
    } else if (this.empType == 0) {
      return this.translateService.instant('รายวัน')
    } else {
      return "-"
    }
  }

  getRole(): string {
    if (this.companyRoleType == 1) {
      return this.translateService.instant('ผู้ดูแลบริษัท')
    } else if (this.companyRoleType == 0) {
      return this.translateService.instant('พนักงาน')
    } else {
      return "-"
    }
  }
}
