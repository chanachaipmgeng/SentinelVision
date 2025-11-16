import { TranslateService } from "@ngx-translate/core";
import { BaseModel } from "./base.model";
import { UserProfileModel } from "./user.model";
import { environment } from "src/environments/environment";

export class CompanyModel extends BaseModel {
  companyName: string;
  companyCode: string;
  companyInfo: string;
  address: string;
  latitude: number;
  longitude: number;
  status: number;
  companyId: string;
  created_at: string;
  updated_at: string;
  picture: string;
  ownerName: string;
  contact: string;

  constructor(
    data?: Partial<CompanyModel>,
    translateService?: TranslateService
  ) {
    super(data, translateService);
    this.companyId = data?.companyId!
    this.companyName = data?.companyName!;
    this.companyCode = data?.companyCode!;
    this.companyInfo = data?.companyInfo!;
    this.address = data?.address!;
    this.latitude = data?.latitude!;
    this.longitude = data?.longitude!;
    this.status = data?.status!;
    this.picture = data?.picture!;
    this.ownerName = data?.ownerName!
    this.contact = data?.contact!
    this.created_at = data?.created_at!
    this.updated_at = data?.updated_at!
  }

  getStatus(): string {
    if (this.status == 1) {
      return this.translateService.instant('PUBLIC')
    } else {
      return this.translateService.instant('PENDING')
    }
  }

  getPicture(): string {
    return environment.baseUrl + '/images/' + this.picture
  }
}
