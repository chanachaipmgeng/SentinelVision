import { TranslateService } from "@ngx-translate/core";
import { BaseModel } from "./base.model";
import { environment } from "../../../environments/environment";

export class UserProfileModel extends BaseModel {
  memberId: string;
  username: string;
  password: string;
  email: string;
  firstName: string;
  lastName: string;
  phoneNumber: string;
  role: number;
  status: number;
  picture: any;
  createdAt: string;
  updatedAt: string;
  constructor(
    data?: Partial<UserProfileModel>,
    translateService?: TranslateService
  ) {
    super(data, translateService);
    this.memberId = data?.memberId!;
    this.username = data?.username!
    this.password = data?.password!
    this.phoneNumber = data?.phoneNumber || ""
    this.firstName = data?.firstName || ""
    this.lastName = data?.lastName || ""
    this.status = data?.status!
    this.email = data?.email!
    this.role = data?.role!
    this.createdAt = data?.createdAt!
    this.updatedAt = data?.updatedAt!
  }

  getRole(): string {
    if (this.role == 99) {
      return this.translateService.instant('Admin-System')
    }
    else if (this.role == 1) {
      return this.translateService.instant('Admin-Company')
    } else {
      return this.translateService.instant('User')
    }
  }

  getStatus(): string {
    if (this.status == 1) {
      return this.translateService.instant('Active')
    } else {
      return this.translateService.instant('Unactive')
    }
  }

  getPicture(): string {
    return this.picture ? environment.baseUrl + '/images/' + this.picture : './assets/images/faces/1.jpg'
  }

  getFullname(): string {
    return this.firstName + " " + this.lastName
  }
}
