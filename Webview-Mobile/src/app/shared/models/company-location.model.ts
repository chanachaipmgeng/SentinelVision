import { TranslateService } from "@ngx-translate/core";
import { BaseModel } from "./base.model";

export class CompanyLocationModel extends BaseModel{
  companyId: string
  locationId: string
  latitude: number
  longitude: number
  radius: number
  locationName: string
  startDate: string
  endDate: string
  locationType: number
  createdAt: string
  updatedAt: string
  constructor(
    data?: Partial<CompanyLocationModel>,
    translateService? : TranslateService
  ) {
    super(data,translateService);
    this.companyId = data?.companyId!
    this.locationId = data?.locationId!
    this.latitude = data?.latitude!
    this.longitude = data?.longitude!;
    this.locationName = data?.locationName!;
    this.startDate = data?.startDate!;
    this.endDate = data?.endDate!
    this.locationType = data?.locationType!
    this.createdAt = data?.createdAt!;
    this.updatedAt = data?.updatedAt!
    this.radius = data?.radius!
  }

  getStatus(): string {
    if (this.locationType == 1) {
      return this.translateService.instant('TEMPORARY')
    } else {
      return this.translateService.instant('PERMANENT')
    }
  }
}
