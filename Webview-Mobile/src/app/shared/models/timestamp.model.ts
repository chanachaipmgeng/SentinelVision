import { TranslateService } from "@ngx-translate/core";
import { BaseModel } from "./base.model";
import { EmployeeModel } from "./employee.model";
import { environment } from "src/environments/environment";

export class TimestampModel extends BaseModel {
  company_employeeId: string
  timestampType: number
  locationName: string
  latitude: number
  longitude: number
  photoTimestamp: string
  timestampId: string
  companyId: string
  timestamp: string
  createdAt: string
  updatedAt: string
  note?: string
  approvalStatus?: string
  approvedBy?: string
  approvedAt?: string
  rejectReason?: string
  employee: EmployeeModel
  constructor(
    data?: Partial<TimestampModel>,
    translateService?: TranslateService
  ) {
    super(data, translateService);
    this.company_employeeId = data?.company_employeeId!
    this.companyId = data?.companyId!
    this.timestampId = data?.timestampId!
    this.locationName = data?.locationName!
    this.latitude = data?.latitude!
    this.longitude = data?.longitude!;
    this.timestampType = data?.timestampType!;
    this.timestamp = data?.timestamp!
    this.photoTimestamp = data?.photoTimestamp!
    this.createdAt = data?.createdAt!;
    this.updatedAt = data?.updatedAt!
    this.note = data?.note || ""
    this.approvalStatus = data?.approvalStatus || "NONE"
    this.approvedBy = data?.approvedBy
    this.approvedAt = data?.approvedAt
    this.rejectReason = data?.rejectReason || ""
    this.employee = new EmployeeModel(data?.employee, this.translateService)
  }

  getStatus(): string {
    if (this.approvalStatus === 'PENDING') {
      return this.translateService.instant('Pending Approval')
    } else if (this.approvalStatus === 'APPROVED') {
      return this.translateService.instant('Approved')
    } else if (this.approvalStatus === 'REJECTED') {
      return this.translateService.instant('Rejected')
    } else if (this.timestampType == 1) {
      return this.translateService.instant('Complete')
    } else if (this.timestampType == 2) {
      return this.translateService.instant('Complete')
    } else if (this.timestampType == 0) {
      return this.translateService.instant('WARNING')
    } else if (this.timestampType == 3) {
      return this.translateService.instant('Absent')
    } else {
      return "-"
    }
  }

  getPicture(): string {
    return this.photoTimestamp ? environment.baseUrl + '/images/' + this.photoTimestamp : './assets/images/faces/1.jpg'
  }

  getLocation(): string {
    return this.locationName ? this.locationName : "ไม่ทราบสถานที่"
  }
}
