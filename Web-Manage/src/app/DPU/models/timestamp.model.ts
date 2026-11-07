import { TranslateService } from "@ngx-translate/core";
import { BaseModel } from "./base.model";
import { EmployeeModel } from "./employee.model";
import { environment } from "../../../environments/environment";

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
  isLate?: boolean
  lateMinutes?: number
  overtimeMinutes?: number
  shiftName?: string
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
    this.latitude = this.toCoord(data?.latitude, 13.7563);
    this.longitude = this.toCoord(data?.longitude, 100.5018);
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
    this.isLate = Boolean(data?.isLate)
    this.lateMinutes = Number(data?.lateMinutes || 0)
    this.overtimeMinutes = Number(data?.overtimeMinutes || 0)
    this.shiftName = data?.shiftName || ""
    this.employee = new EmployeeModel(data?.employee, this.translateService)
  }

  getStatus(): string {
    if (this.approvalStatus === 'PENDING') {
      return this.translateService ? this.translateService.instant('Pending Approval') : 'รออนุมัติ'
    } else if (this.approvalStatus === 'APPROVED') {
      return this.translateService ? this.translateService.instant('Approved') : 'อนุมัติแล้ว'
    } else if (this.approvalStatus === 'REJECTED') {
      return this.translateService ? this.translateService.instant('Rejected') : 'ไม่อนุมัติ'
    } else if (this.timestampType == 1) {
      if (this.isLate && (this.lateMinutes || 0) > 0) {
        return `เข้างาน (สาย ${this.lateMinutes} นาที)`
      }
      return 'เข้างานปกติ'
    } else if (this.timestampType == 2) {
      if ((this.overtimeMinutes || 0) > 0) {
        return `ออกงาน (OT ${this.overtimeMinutes} นาที)`
      }
      return 'ออกงานปกติ'
    } else if (this.timestampType == 0) {
      return this.translateService ? this.translateService.instant('WARNING') : 'Warning (นอกพื้นที่)'
    } else if (this.timestampType == 3) {
      return this.translateService ? this.translateService.instant('Absent') : 'Absent'
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

  private toCoord(value: unknown, fallback: number): number {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }
}
