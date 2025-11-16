import { TranslateService } from "@ngx-translate/core";
import { BaseModel } from "./base.model";

export interface UserRoleModel {
  roleId: string;
  thName: string;
  engName: string;
  level: string;
  status: string;
  pwWrong: number;
  pwWaitingTime: number;
  pwMax: number;
  pwMin: number;
  pwStr: number;
  pwStrSm: number;
  pwNumber: number;
  pwSpecial: number;
  getName(): string
  getStatus(): string
}

export class UserRole extends BaseModel implements UserRoleModel {
  roleId: string;
  thName: string;
  engName: string;
  level: string;
  status: string;
  pwWrong: number;
  pwWaitingTime: number;
  pwMax: number;
  pwMin: number;
  pwStr: number;
  pwStrSm: number;
  pwNumber: number;
  pwSpecial: number;

  constructor(
    data?: Partial<UserRoleModel>,
    translateService?: TranslateService
  ) {
    super(data, translateService);
    this.roleId = data?.roleId!;
    this.thName = data?.thName!;
    this.engName = data?.engName!;
    this.level = data?.level!;
    this.status = data?.status ? data.status : 'U';
    this.pwWrong = data?.pwWrong!;
    this.pwWaitingTime = data?.pwWaitingTime!;
    this.pwMax = data?.pwMax!;
    this.pwMin = data?.pwMin!;
    this.pwStr = data?.pwStr!;
    this.pwStrSm = data?.pwStrSm!;
    this.pwNumber = data?.pwNumber!;
    this.pwSpecial = data?.pwSpecial!;
  }

  getName(): string {
    return this.translateService.currentLang == "th"
      ? this.thName
      : this.engName;
  }

  getStatus(): string {
    if (this.status == 'A') {
      return this.translateService.instant('Active')
    } else {
      return this.translateService.instant('Unactive')
    }
  }
}
